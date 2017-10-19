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
        self.log('Assigned supply: {}'.format(assigned_supply))
    
    def get_total_supply(self):
        total_supply = self.contract.call({ 'from': self._from }).totalSupply()
        self.log('Total supply: {}'.format(total_supply))

    def get_gmt_balance_of(self, address):
        balance = self.contract.call({ 'from': self._from }).balanceOf(self._from) / 10**18
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
                    Sale started. Transaction in progress. 
                    Transaction hash: {}""".format(restart_sale_transaction_hash))
      
    def stop_sale(self):
        stop_sale_transaction_hash = self.contract.transact({ 'from': self._from }).stopSale()
        self.log("""
                    Sale stopped. Transaction in progress. 
                    Transaction hash: {}""".format(stop_sale_transaction_hash))

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
                          Exchange rate: {}""".format(
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
                          exchange_rate)

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
@click.option('--gas-price', default=20000000000, help='Transaction gas price')
@click.option('--contract-addr', help='Address of contract to interact with')
@click.option('--account', help='Default account used as from parameter')
@click.option('--private-key-path', help='Path to private key')
def setup(protocol, host, port, gas, gas_price, contract_addr, account, private_key_path):
    transactions_handler = Transactions_Handler(protocol, host, port, gas, gas_price, contract_addr, account, private_key_path)
    # transactions_handler.get_metadata()
    # transactions_handler.restart_sale()
    # transactions_handler.stop_sale()
    # transactions_handler.get_assigned_supply()
    # transactions_handler.change_owner('NEW ADDRESS')
    # transactions_handler.get_transaction_receipt('TRANSACTION_HASH')
    # transactions_handler.get_nonce()
    # transactions_handler.estimate_gas()
    # transactions_handler.is_registered('0x3f2448C5B367A5aD372D1b9D1cEB17E19E0F8577')
    addresses = ["0x20ce23c5eB560E3ECB2BEf048609b89B6a44C3fB","0x25E6931b8Afb69fE53CEaBF735586138eC1B706F","0x74d66d84B88eA71108c7398aceC26530F1B64E0b","0x22ab445A54FeE7fe41B9EB559Dde71Dd1D91991A","0xa3A13AcF461f494240Ae54801fDEd688D2e2b16a","0x5b51f89c077ccA89b146022e8de9f72deEcd7955","0xf3258938D09AE9aaa2D6d3E89CE1244da4474950","0xddD7347A8d3605F35A6113c7513e388e1A51bCB5","0xd452b938c37d965154b3f52fBb6D13e032562E2e","0x490D8abA74Ecc9664CAf5F3ae7f7dFf57934fEE8","0xc52E6380983Fd52E663E8B596391Df65e3d1C02F","0xA862112b2dC553a73Efb40155879eb1bB2Caca86","0xC61Ba4DaAa2F3446D367D3e701C47189C1B223b8","0xe692b22a006ad7A3cf392C9dc40F56C45e155df5","0x1b2d6c5A3B2bBBd5BD9688eCafDdC7920E53ab61","0x524a063fe0a1D52ba6E71bF813233590dd8Efe41","0x50414B85E1F59beE5639B2d0ff9eAd3695079FDe","0x179D1A2543745958D7f90A5c0040e467C25cd4fE","0x88B164e589331Db3AAEc043c6d8da00e36853b34","0x2D7DAFeC5C81d0046410845b0d15c00074bb73a1","0xC4dFf0CAb36f3a10e965E9028ecac073b25f2AB5","0x8eB1b5f4369c9AfB4B5482EdcF7d802195D5Db89","0xE57798f2e67Ded880Bd5cF524418eAE3fbfA8CA6","0xDC65205f54c806535375d4eEFDED606Cd957e66B","0x6494bC076E14828ab0b119b94C7731222fF115a9","0xcD2C45d2dE4EcB845B21F9A8759D0D9E67b45ebd","0x053141C3e486d30832B4432a327A3eb4e2CD3f09","0xc3BEE64137FF35b735c4F4d0d0a07dAa50c59bf1","0x0c19ff8d1e915cd62A638683909EfE30e63207E0","0x726d95C858dF19DA927C9CE1D1d1d224Cc4574bD","0x49adFb135996449A23e236B199BC6cFfBE92bC78","0x2b251d772e2650e84289Ba65a8e5F4005e800dbF","0xa6A72baA69eD88FE6da8cBd932267dF426735A56","0xaC71C6CAe468C7ffc72A9813E32cd317BbE309aD","0x4eF68F0FaD563190be9c8ccD83c09A6771d33566","0x364842C8ab60BDa9c490DA6ECE9568fd32461c24","0xA7Db568247b2050AD44005b283b301d832ceC653","0x39BB6d09afd5DB0F432c8072C14845eA29a09272","0x3E6B4eCe4931d9DeEFaaD665fd2260DdD40330a9","0x3dbe0a3e0fa494c5c012cf5b6b2caa5ed5312376","0x1D753316dcee2dF1120A1CaeC256907100d0b32F","0xDcf213cF5FA361C0D56e03b5aE811Bd1F105C0d7","0x331C01A1866f4AC4Cf7C13Bd87631Ab6ca5D2307","0x708746d07fBFea9eB83583452940B84438C5a1EB","0x9f5a3CfA52c0719e96922Aa28a0F450636B094d1","0xD993360912CCb7F229baaE689f5C24dc5A7072Dd","0xF86A27283c7C4Ef1C676a0E6b810Ac8ccCc39ECb","0x543424f9Cf556285Ddb9107910B5A1c10f6F4bD6","0xd642d098EE4e4eCed24B12BeDcD06dAc20f5e541","0x4870bB31A892374a3E81FA17833C10946DDB5223","0x51D390F35001969B2db7EA0b5Dee970ec55d3647","0x6d8377467574d81D5E6d7F05FfEE191fcd0cE0d8","0x04D57c783101d40859e0433a3488cDF1CA1f29b6","0x0790C57C2109705627883dB512dD118f046aB5F6","0x924C251902924c7DBd4cBF166d42757fB2d146cb","0x2244D06599c38EF6b1ca2F334735BFea4CE45392","0xF1D0bBe6D450F4B2703388a81F144BFD1d1558C1","0x924C2e5d25fAf0225122bF62CFfe99e27312E45a","0x9A0b50EFECfb37E42DB9A603893003B91FdB5e87","0x5e40682a189314EE0C15E28FebE301E51EA31148","0x6A5D761F8C0766763F4BAc213E1B44cA120c83DE","0xc81d14595feeF32f476cb56A805eF0139354A5b9","0x4A254BCA4F7eA6C8f7dbb6282a3d98f7c084BDE6","0x2F39437CD069ee21821eba2C9E4A4Fa853E8F144","0xE84fe89D0E2638AEe6fEee94Ed73bdbD35B18442","0x6EcEeDA2D620B0F0C8aF615984007737B7dD25D0","0x04eFdcfD5c1AD83E1793F370A6A0Ba9d748AA2F9","0xFAB3F2796cbA34b65ef40653e1f2DDb48Ddced90","0x7f71f6b28Eb2f60691c0D3DEB016106046c21d15","0xdf031133Fa7cF375dEC4bE7C37b097E19003519f","0x004736B7482D8f8E62B9bc0e800Dc80813E7E84D","0xda24669C6395Eab66a857E36CCb48ABD30a196ee","0xa5C1D8DCD76aA8Fc7624A9c888aBD8F06a261839","0x3dDeDD73c58Fd6dd34Ba56d8bFffD27ff3594F72","0x8D3eA82192AFAAeCF3675ED7686De1d3D83005de","0x00a65c76665C4E5094c9B1e70EE7021eb95e0C42","0x3F4aF4c68AA4Adb99606A2c05C07BFa6528D2341","0x83905F205a22cff5f790D06b8D1c9Fc49f14eC40","0xDCf48f8AB66B7a15410847F9BcFf6fc989a36bb7","0xd6C0C5A07f42E07089A59a79476AF756F310Cb81","0x7F50397078Ad4dA62c4e2eB6A5e4503D36E50bB2","0x04A853C5551ce0C1AAcdAdB82b3723c695A7716D","0x92f5B1664E03F1b8fF617C86905fd17e0B18E76F","0x953Cd3772C127B15D40f7c8b3340cff9fa5df932","0x7b687BfB62E2AbB56269Df7c5aADAfB706AA316A","0x8bD865bE7082d9764ff34366882542fA5Bfe9725","0x13Ce9A262EFb94B277e622c90405Ae8C93C1A4e2","0x74430A7DC30960952075e480AD841B6A092765d1","0x726C2EE3bb63B6e9B9b0229cCAa02F691BB0b5dd","0x378B2d21E485d7098a2967c01F3F58007C09aC27","0x3ECBA7de7E9aB4EC1FFd409146F8EDC892dDcEd7","0x9DA74B6EB82484c8592AdF49352fb5014A5Dc6AA","0x68F3e88D97e6F70B1e8ffAE367d24f5a02022cfA","0xB0195d54910840Ed7BAcE08d79BE9C34Bb93d3eC","0x422d5f48200fc1BaEf529bA7B9b176303e957A82","0x00d6041404eBC2A778b48c29F952244b2815f0b5","0xee083EDCADF67065aa51db510d643E8c0dB6f5A5"]
    transactions_handler.change_registration_statuses(addresses, True)
    # transactions_handler.claim_tokens(20000)
    # transactions_handler.finalize()

if __name__ == '__main__':
  setup()
