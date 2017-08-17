from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed
from ethereum.tools import tester
from ethereum.utils import privtoaddr, sha3, to_string, encode_hex

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.safe.test_gmt_safe
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)
        # NOTE: balances default to 1 ETH
        self.gmt_wallet_address = accounts[1]
        self.eth_wallet_address = accounts[2]
        self.test_allocation_account = accounts[5]
        self.startBlock = 4097906
        self.saleDuration = round((30*60*60*24)/18)
        self.endBlock = self.startBlock + self.saleDuration
        self.exchangeRate = 4316
        self.gmt_token= self.create_contract('Tokens/GMTokenTestFile.sol',
                                                args=(self.eth_wallet_address,
                                                self.gmt_wallet_address,
                                                self.startBlock,
                                                self.endBlock))
        self.gmt_safe = self.create_contract('Safe/GMTSafeTestFile.sol', args=[self.gmt_wallet_address])
        
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 4
        value_1 = 39200 * 10**18 # 39.2k Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.c.head_state.block_number = self.endBlock + 1
        self.gmt_token.finalize()

        # Transfer 1000 GMT from GMT fund (i.e. account 1) to this GMT Safe contract
        self.gmt_token.transfer(self.gmt_safe.address, 1000, sender=keys[1])
        
        self.lockedPeriod = 6 * 30 * 60 * 60 * 24 # 180 days

    def test_initial_state(self):
        self.assertEqual(self.gmt_safe.unlockDate(), self.c.head_state.timestamp + self.lockedPeriod)
        self.assertEqual(self.gmt_safe.gmtAddress(), '0x' + self.gmt_wallet_address.hex())

    def test_unauthorized_unlock(self):
        # Raises if someone without allocations tries to unlock
        self.assertRaises(TransactionFailed, self.gmt_safe.unlock, sender=keys[8])

    def test_unlock_before_unlock_period_ends(self):
        # Raises if someone tries to unlock the allocations before unlock date
        self.c.head_state.timestamp = self.c.head_state.timestamp + self.lockedPeriod - 100

        self.assertRaises(TransactionFailed, self.gmt_safe.unlock, sender=keys[5])
    
    def test_unlock(self):
        # Raises if owner tries to unlock the allocations before unlock date
        self.c.head_state.timestamp = self.c.head_state.timestamp + self.lockedPeriod + 100
        
        self.gmt_safe.unlock(sender=keys[5])
        # self.assertRaises(TransactionFailed, self.gmt_safe.unlock, sender=keys[0])