from web3 import Web3, KeepAliveRPCProvider, IPCProvider
from ethereum.abi import ContractTranslator
from ethereum.transactions import Transaction
from ethereum.utils import privtoaddr
from ethereum import _solidity
import click
import time
import json
import rlp
import logging
import os


# create logger
logger = logging.getLogger('DEPLOY')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class EthDeploy:

    def __init__(self, protocol, host, port, gas, gas_price, contract_dir, optimize, account, private_key_path):
        # Establish rpc connection
        self.web3 = Web3(KeepAliveRPCProvider(host=host, port=port))
        self.solidity = _solidity.solc_wrapper()
        self._from = None
        self.private_key = None

        # Set sending account
        if account:
            self._from = self.add_0x(account)
        elif private_key_path:
            with open(private_key_path, 'r') as private_key_file:
                self.private_key = private_key_file.read().strip()
            self._from = self.add_0x(privtoaddr(self.private_key.decode('hex')).encode('hex'))
        else:
            accounts = self.web3.eth.accounts
            if len(accounts) == 0:
                raise ValueError('No account unlocked')
            self._from = self.add_0x(accounts[0])

        # Check if account address in right format
        if not self.is_address(self._from):
            raise ValueError('Account address is wrong')

        # Set deployment configuration
        self.optimize = optimize
        self.contract_dir = contract_dir
        self.gas = gas
        self.gas_price = gas_price

        # References dict maps labels to addresses
        self.references = {}

        # Abis dict maps addresses to abis
        self.abis = {}

        # Total consumed gas
        self.total_gas = 0

        self.log('Instructions are sent from address: {}'.format(self._from))

        balance = self.web3.eth.getBalance(self._from)
        self.log('Address balance: {} Ether / {} Wei'.format(balance/10.0**18, balance))

    def is_address(self, string):
        return len(self.add_0x(string)) == 42

    @staticmethod
    def hex2int(_hex):
        return int(_hex, 16)

    @staticmethod
    def add_0x(string):
        if not string.startswith('0x'):
            return '0x' + string
        return string

    @staticmethod
    def strip_0x(string):
        if string.startswith('0x'):
            return string[2:]
        return string

    @staticmethod
    def log(string):
        logger.info(string)

    def format_reference(self, string):
        return self.add_0x(string) if self.is_address(string) else string

    def log_transaction_receipt(self, transaction_receipt):
        gas_used = transaction_receipt['gasUsed']
        self.total_gas += gas_used
        self.log('Transaction receipt: {} block number, {} gas used, {} cumulative gas used'.format(
            transaction_receipt['blockNumber'],
            gas_used,
            transaction_receipt['cumulativeGasUsed']
        ))

    def get_transaction_receipt(self, transaction_hash):
        return self.web3.eth.getTransactionReceipt(transaction_hash)

    def replace_references(self, a):
        if isinstance(a, list):
            return [self.replace_references(i) for i in a]
        else:
            return self.references[a] if isinstance(a, str) and a in self.references else a

    def get_nonce(self):
        transaction_count = self.json_rpc.eth_getTransactionCount(self._from, default_block='pending')['result']
        return self.hex2int(self.strip_0x(transaction_count))

    def compile_code(self, code=None, path=None):
        # Create list of valid paths
        absolute_path = self.contract_dir if self.contract_dir.startswith('/') else '{}/{}'.format(os.getcwd(),
                                                                                                   self.contract_dir)
        sub_dirs = [x[0] for x in os.walk(absolute_path)]
        extra_args = ' '.join(['{}={}'.format(d.split('/')[-1], d) for d in sub_dirs])
        # Compile code
        combined = self.solidity.combined(code, path=path, extra_args=extra_args)
        bytecode = combined[-1][1]['bin_hex']
        abi = combined[-1][1]['abi']
        return bytecode, abi

    def deploy(self, _from, file_path, bytecode, sourcecode, libraries, value, params, label, abi):
        # Replace library placeholders
        if libraries:
            for library_name, library_address in libraries.iteritems():
                self.references[library_name] = self.replace_references(self.strip_0x(library_address))

        if file_path:
            if self.contract_dir:
                file_path = '{}/{}'.format(self.contract_dir, file_path)
            bytecode, abi = self.compile_code(path=file_path)
            if not label:
                label = file_path.split("/")[-1].split(".")[0]

        if sourcecode:
            # Compile code
            bytecode, abi = self.compile_code(code=sourcecode)

        if params:
            translator = ContractTranslator(abi)
            # Replace constructor placeholders
            params = [self.replace_references(p) for p in params]
            bytecode += translator.encode_constructor_arguments(params).hex()

        # Deploy contract
        self.log('Deployment transaction for {} sent'.format(label if label else 'unknown'))
        tx_response = None
        tx = {'from':self._from, 
                  'value':value,
                  'data':self.add_0x(bytecode), 
                  'gas':self.gas,
                  'gas_price':self.gas_price}

        # Send contract creation transaction
        if self.private_key:
            tx = Transaction(tx)
            nonce = self.web3.eth.getTransactionCount(self._from)
            tx['nonce'] = nonce
            tx.sign(self.private_key)
            raw_tx = rlp.encode(tx)
            while tx_response is None or 'error' in tx_response:
                if tx_response and 'error' in tx_response:
                    self.log('Deploy failed with error {}'.format(tx_response['error']['message']))
                    time.sleep(5)
                self.web3.eth.sendRawTransaction(raw_tx)
                tx_response = self.web3.eth.sendRawTransaction(raw_tx)
        else:
            while tx_response is None or 'error' in tx_response:
                if tx_response and 'error' in tx_response:
                    self.log('Deploy failed with error {}'.format(tx_response['error']['message']))
                    time.sleep(5)
                tx_response = self.web3.eth.sendTransaction(tx)
        
        # Generate transaction receipt
        transaction_receipt = self.web3.eth.getTransactionReceipt(tx_response)

        contract_address = transaction_receipt['contractAddress']
        self.references[label] = contract_address
        self.abis[contract_address] = abi
        self.log('Contract {} created at address {}'.format(label if label else 'unknown',
                                                            self.add_0x(contract_address)))
        self.log_transaction_receipt(transaction_receipt)

    def process(self, f):
        # Read instructions file
        with open(f, 'r') as instructions_file:
            instructions = json.load(instructions_file)
        for i in instructions:
            if i['type'] == 'abi':
                for address in i['addresses']:
                    self.abis[self.strip_0x(address)] = i['abi']
            if i['type'] == 'deployment':
                self.deploy(
                    i['from'] if 'from' in i else None,
                    i['file'] if 'file' in i else None,
                    i['bytecode'] if 'bytecode' in i else None,
                    i['sourcecode'] if 'sourcecode' in i else None,
                    i['libraries'] if 'libraries' in i else None,
                    i['value'] if 'value' in i else 0,
                    i['params'] if 'params' in i else (),
                    i['label'] if 'label' in i else None,
                    i['abi'] if 'abi' in i else None
                )

        self.log('-'*96)
        self.log('Summary: {} gas used, {} Ether / {} Wei spent on gas'.format(self.total_gas,
                                                                               self.total_gas*self.gas_price/10.0**18,
                                                                               self.total_gas*self.gas_price))
        for reference, value in self.references.items():
            self.log('{} references {}'.format(reference, self.add_0x(value) if isinstance(value, str) else value))
        self.log('-' * 96)


@click.command()
@click.option('--f', help='File with instructions')
@click.option('--protocol', default="http", help='Ethereum node protocol')
@click.option('--host', default="localhost", help='Ethereum node host')
@click.option('--port', default='8545', help='Ethereum node port')
@click.option('--gas', default=4000000, help='Transaction gas')
@click.option('--gas-price', default=20000000000, help='Transaction gas price')
@click.option('--contract-dir', default="contracts/", help='Path to contracts directory')
@click.option('--optimize', is_flag=True, help='Use solidity optimizer to compile code')
@click.option('--account', help='Default account used as from parameter')
@click.option('--private-key-path', help='Path to private key')
def setup(f, protocol, host, port, gas, gas_price, contract_dir, optimize, account, private_key_path):
    deploy = EthDeploy(protocol, host, port, gas, gas_price, contract_dir, optimize, account, private_key_path)
    deploy.process(f)

if __name__ == '__main__':
    setup()
