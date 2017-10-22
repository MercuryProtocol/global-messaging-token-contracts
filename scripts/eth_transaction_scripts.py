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
        assigned_supply = self.contract.call({ 'from': self._from }).assignedSupply() / 10**18
        self.log('Assigned supply (adjusted for token unit): {}'.format(assigned_supply))
    
    def get_total_supply(self):
        total_supply = self.contract.call({ 'from': self._from }).totalSupply()
        self.log('Total supply: {}'.format(total_supply))

    def get_gmt_balance_of(self, address):
        balance = self.contract.call({ 'from': self._from }).balanceOf(address) / 10**18
        self.log('Address: {} | Balance: {}'.format(address, balance))

    def get_eth_balance_of(self, address):
        balance = self.web3.eth.getBalance(self._from)
        self.log("Balance for address {} is {} Ether / {} Wei".format(address, balance/10**18, balance))
    
    def change_owner(self, address):
        self.contract.transact({ 'from': self._from }).changeOwner(address)
        self.log("Owner for contract changed from {} to {}".format(self._from, address))

    def change_registration_status(self, address, status):
        change_registration_status_transaction_hash = self.contract.transact({ 'from': self._from }).changeRegistrationStatus(address, status)
        self.log("Transaction hash: {}".format(change_registration_status_transaction_hash))
    
    def change_registration_statuses(self, addressesArray, status):
        change_registration_status_transaction_hash = self.contract.transact({ 'from': self._from }).changeRegistrationStatuses(addressesArray, status)
        self.log("Transaction hash: {}".format(change_registration_status_transaction_hash))

    def is_registered(self, address):
        registered = self.contract.call({ 'from': self._from }).registered(address)
        self.log('Is {} Registered: {}'.format(address, registered))

    def restart_sale(self):
        restart_sale_transaction_hash = self.contract.transact({ 'from': self._from }).restartSale()
        self.log("""
                    Sale restarted. Transaction in progress. 
                    Transaction hash: {}""".format(restart_sale_transaction_hash))
      
    def stop_sale(self):
        stop_sale_transaction_hash = self.contract.transact({ 'from': self._from }).stopSale()
        self.log("""
                    Sale stopped. Transaction in progress. 
                    Transaction hash: {}""".format(stop_sale_transaction_hash))

    def is_stopped(self):
        is_stopped = self.contract.call({ 'from': self._from }).isStopped()
        self.log("""
                    Sale stopped: {}""".format(is_stopped))

    def is_finalized(self):
        is_finalized = self.contract.call({ 'from': self._from }).isFinalized()
        self.log("""
                    Sale finalized: {}""".format(is_finalized))

    def claim_tokens(self, value):
        claim_tokens_transaction_hash = self.contract.transact({ 'from': self._from, 'value': value }).claimTokens()
        balance = self.contract.call({ 'from': self._from }).balanceOf(self._from) / 10**18
        self.log("""
                    Created tokens for {}. Transaction in progress. 
                    Transaction hash: {}
                    GMT Balance: {}""".format(
                    self._from, 
                    claim_tokens_transaction_hash,
                    balance))
    
    def finalize(self):
        finalize_transaction_hash = self.contract.transact({ 'from': self._from }).finalize()
        self.log("""
                    Sale finalized. Transaction in progress. 
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
        exchange_rate = self.contract.call({ 'from': self._from }).tokenExchangeRate()
        baseTokenCapPerAddress = self.contract.call({ 'from': self._from }).baseTokenCapPerAddress()

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
                          Exchange rate: {}
                          Base token cap per address: {}""".format(
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
                          exchange_rate,
                          baseTokenCapPerAddress)

        self.log(log_output)

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
        receipt = self.web3.eth.getTransactionReceipt(transaction_hash)
        self.log("Transaction Receipt: {}".format(receipt))
        return receipt
    
    def estimate_gas(self):
        gas_estimate = self.contract.estimateGas().changeRegistrationStatuses(['TBU'], True)
        self.log("Gas estimate: {}".format(gas_estimate))
        return gas_estimate

    def replace_references(self, a):
        if isinstance(a, list):
            return [self.replace_references(i) for i in a]
        else:
            return self.references[a] if isinstance(a, str) and a in self.references else a

    def get_nonce(self):
        transaction_count = self.web3.eth.getTransactionCount(self._from)
        self.log("Nonce: {}".format(transaction_count))
        return transaction_count


@click.command()
@click.option('--protocol', default="http", help='Ethereum node protocol')
@click.option('--host', default="localhost", help='Ethereum node host')
@click.option('--port', default='8545', help='Ethereum node port')
@click.option('--gas', default=4000000, help='Transaction gas')
@click.option('--gas-price', default=31000000000, help='Transaction gas price')
@click.option('--contract-addr', help='Address of contract to interact with')
@click.option('--account', help='Default account used as from parameter')
@click.option('--private-key-path', help='Path to private key')
def setup(protocol, host, port, gas, gas_price, contract_addr, account, private_key_path):
    transactions_handler = Transactions_Handler(protocol, host, port, gas, gas_price, contract_addr, account, private_key_path)
    # transactions_handler.get_metadata()
    # transactions_handler.restart_sale()
    # transactions_handler.stop_sale()
    # transactions_handler.is_stopped()
    # transactions_handler.is_finalized()
    # transactions_handler.get_assigned_supply()
    # transactions_handler.change_owner('NEW ADDRESS')
    # transactions_handler.get_transaction_receipt('TRANSACTION_HASH')
    # transactions_handler.get_nonce()
    # transactions_handler.estimate_gas()
    # transactions_handler.is_registered('ADDRESS')
    # transactions_handler.is_registered('ADDRESS')
    addresses_1 = []
    addresses_2 = []
    # transactions_handler.change_registration_statuses(addresses_1, True)
    # transactions_handler.claim_tokens(1100000000000000000)
    # transactions_handler.get_gmt_balance_of("0x04ca6ceFeB15E82Ce3f156f4cD8727571E94b99c")
    transactions_handler.finalize()

if __name__ == '__main__':
  setup()
