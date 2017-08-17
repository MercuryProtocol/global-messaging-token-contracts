from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed
from ethereum.tools import tester
from ethereum.utils import privtoaddr

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.safe.test_gmt_safe
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)
        # NOTE: balances default to 1 ETH
        self.gmt_wallet_address = accounts[1]
        self.gmt_token= self.create_contract('Safe/GMTSafeTestFile.sol', args=[self.gmt_wallet_address])
        self.owner = self.gmt_token.owner()    

    def test_initial_state(self):
        self.assertEqual(self.gmt_token.owner(), '0x' + accounts[0].hex())