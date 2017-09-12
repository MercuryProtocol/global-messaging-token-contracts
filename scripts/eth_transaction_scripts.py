from web3 import Web3, KeepAliveRPCProvider, IPCProvider
from ethereum.abi import ContractTranslator
from ethereum.transactions import Transaction
from ethereum.utils import privtoaddr
from ethereum.tools import _solidity
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


class Transactions_Handler:

    def __init__(self, protocol, host, port, gas, gas_price, contract_addr, account, private_key_path):
        # Establish rpc connection
        self.web3 = Web3(KeepAliveRPCProvider(host=host, port=port))
        self.solidity = _solidity.solc_wrapper()
        self._from = None
        self.private_key = None
        self.abi = None
        self.contract_addr = contract_addr

        fn = os.path.join(os.path.dirname(__file__), 'deployed_abis.json')
        with open(fn, 'r') as instructions_file:
            instructions = json.load(instructions_file)
            self.abi = instructions[self.contract_addr]

        self.contract = self.web3.eth.contract(address=self.contract_addr, abi=self.abi)

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

        self.gas = gas
        self.gas_price = gas_price

        # Total consumed gas
        self.total_gas = 0

        self.log('Instructions are sent from address: {}'.format(self._from))

        balance = self.web3.eth.getBalance(self._from)

        self.log('Address balance: {} Ether / {} Wei'.format(balance/10**18, balance))

    def is_address(self, string):
        return len(self.add_0x(string)) == 42

    @staticmethod
    def hex2int(_hex):
        return int(_hex, base=16)

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
    
    def encode_parameters(self, typesArray, parameters):
        return self.web3.eth.abi.encodeParameters(typesArray, parameters)
    
    def get_code(self):
        if contract_addr:
          return self.web3.eth.getCode(self.contract_addr)
        else:
          default_address = list(self.abis.keys())[0]
          return self.web3.eth.getCode(self.abis[default_address]) if default_address else None
    
    def get_owner(self):
        owner = self.contract.call({ 'from': self._from }).owner()
        self.log('Contract owner: {}'.format(owner))

    def get_start_block(self):
        start_block = self.contract.call({ 'from': self._from }).startBlock()
        self.log('Start block: {}'.format(start_block))
      
    def get_end_block(self):
        end_block = self.contract.call({ 'from': self._from }).endBlock()
        self.log('End block: {}'.format(end_block))

    def get_assigned_supply(self):
        assigned_supply = self.contract.call({ 'from': self._from }).assignedSupply()
        self.log('End block: {}'.format(assigned_supply))
    
    def get_total_supply(self):
        total_supply = self.contract.call({ 'from': self._from }).totalSupply()
        self.log('End block: {}'.format(total_supply))
    
    def get_stage(self):
        stage = self.contract.call({ 'from': self._from }).stage()
        self.log('Stage: {}'.format(stage))

    def get_gmt_balance_of(self, address):
        balance = self.contract.call({ 'from': self._from }).balanceOf(self._from) / 10**18
        self.log('Address: {} | Balance: {}'.format(address, balance))

    def get_eth_balance_of(self, address):
        balance = self.web3.eth.getBalance(self._from)
        self.log("Balance for address {} is {} Ether / {} Wei".format(address, balance/10**18, balance))

    def start_sale(self):
        start_sale_transaction_hash = self.contract.transact({ 'from': self._from }).startSale()
        time.sleep(5)
        stage = self.contract.call({ 'from': self._from }).stage()
        self.log("""
                    Sale started. 
                    Current stage: {}
                    Transaction hash: {}""".format(stage, start_sale_transaction_hash))
      
    def stop_sale(self):
        stop_sale_transaction_hash = self.contract.transact({ 'from': self._from }).stopSale()
        time.sleep(5)
        stage = self.contract.call({ 'from': self._from }).stage()
        self.log("""
                    Sale stopped. 
                    Current stage: {}
                    Transaction hash: {}""".format(stage, stop_sale_transaction_hash))
    
    def set_failed_state(self):
        failed_sale_transaction_hash = self.contract.transact({ 'from': self._from }).setFailedState()
        time.sleep(5)
        stage = self.contract.call({ 'from': self._from }).stage()
        self.log("""
                    Sale stopped. 
                    Current stage: {}
                    Transaction hash: {}""".format(stage, failed_sale_transaction_hash))

    def create_tokens(self, value):
        create_tokens_transaction_hash = self.contract.transact({ 'from': self._from, 'value': value }).createTokens()
        time.sleep(5)
        stage = self.contract.call({ 'from': self._from }).stage()
        balance = self.contract.call({ 'from': self._from }).balanceOf(self._from) / 10**18
        self.log("""
                    Created tokens for {} 
                    Transaction hash: {}
                    GMT Balance: {}""".format(
                    self._from, 
                    create_tokens_transaction_hash,
                    balance))
    
    def finalize(self, ):
        finalize_transaction_hash = self.contract.transact({ 'from': self._from }).finalize()
        time.sleep(5)
        stage = self.contract.call({ 'from': self._from }).stage()
        self.log("""
                    Sale finalized.
                    Transaction hash: {}""".format(finalize_transaction_hash))
    
    def get_metadata(self):
        name = self.contract.call({ 'from': self._from }).name()
        symbol = self.contract.call({ 'from': self._from }).symbol()
        decimals = self.contract.call({ 'from': self._from }).decimals()
        owner = self.contract.call({ 'from': self._from }).owner()
        start_block = self.contract.call({ 'from': self._from }).startBlock()
        end_block = self.contract.call({ 'from': self._from }).endBlock()
        assigned_supply = self.contract.call({ 'from': self._from }).assignedSupply()
        total_supply = self.contract.call({ 'from': self._from }).totalSupply()
        gmt_fund_address = self.contract.call({ 'from': self._from }).gmtFundAddress()
        eth_fund_address = self.contract.call({ 'from': self._from }).ethFundAddress()
        stage = self.contract.call({ 'from': self._from }).stage()

        log_output = """
                          METADATA::
                          Name: {}
                          Symbol: {}
                          Decimals: {}
                          Owner: {}
                          Start block: {}
                          End block: {}
                          Assigned supply: {}
                          Total supply: {}
                          GMT fund address: {}
                          ETH fund address: {} 
                          State: {} """.format(
                          name,
                          symbol,
                          decimals,
                          owner,
                          start_block,
                          end_block,
                          assigned_supply,
                          total_supply,
                          gmt_fund_address,
                          eth_fund_address,
                          stage)

        self.log(log_output)

    def send_transaction(self, typesArray, parameters):
        return self.web3.eth.sendTransaction({'to': self.contract_addr, 'from': self._from, 'value': 0})
        # return self.web3.eth.abi.encodeParameters(typesArray, parameters)

    def log_transaction_receipt(self, transaction_receipt):
        block_number = transaction_receipt['blockNumber']
        transaction_hash = transaction_receipt['transactionHash']
        gas_used = transaction_receipt['gasUsed']
        block_hash = transaction_receipt['blockHash']
        contract_address = transaction_receipt['contractAddress']
        cumulative_gas_used = transaction_receipt['cumulativeGasUsed']

        self.total_gas += gas_used

        log_output = """
                        Transaction receipt::
                        Block number: {}
                        Transaction hash: {}
                        Gas used: {}
                        Block hash: {}
                        Contract address: {}
                        Cumulative gas used: {} """.format(
                        block_number,
                        transaction_hash,
                        gas_used,
                        block_hash,
                        contract_address,
                        cumulative_gas_used)

        self.log(log_output)

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


@click.command()
@click.option('--protocol', default="http", help='Ethereum node protocol')
@click.option('--host', default="localhost", help='Ethereum node host')
@click.option('--port', default='8545', help='Ethereum node port')
@click.option('--gas', default=4000000, help='Transaction gas')
@click.option('--gas-price', default=20000000000, help='Transaction gas price')
@click.option('--contract-addr', help='Address of contract to interact with')
@click.option('--account', help='Default account used as from parameter')
@click.option('--private-key-path', help='Path to private key')
def setup(protocol, host, port, gas, gas_price, contract_addr, account, private_key_path):
    transactions_handler = Transactions_Handler(protocol, host, port, gas, gas_price, contract_addr, account, private_key_path)
    transactions_handler.get_metadata()
    amount = 1 * 10**18
    transactions_handler.create_tokens(amount)

if __name__ == '__main__':
  setup()
