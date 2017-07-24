from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed
from ethereum.tools import tester
from ethereum.utils import privtoaddr

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.tokens.test_gmt_token
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)
        self.eth_multisig_wallet_address = accounts[0]
        self.gmt_multisig_wallet_address = accounts[1]
        self.gmt_token= self.create_contract('Tokens/GMTokenAll.sol',
                                                args=(self.eth_multisig_wallet_address, self.gmt_multisig_wallet_address))
        self.owner = self.gmt_token.owner()

    def test_meta_data(self):
        self.assertEqual(self.gmt_token.name().decode(), "Global Messaging Token")
        self.assertEqual(self.gmt_token.symbol().decode(), "GMT")
        self.assertEqual(self.gmt_token.decimals(), 18)

    def test_initial_state(self):
        self.assertEqual(self.gmt_token.totalSupply(), 1000000000 * (10**18))
        self.assertEqual(self.gmt_token.gmtFund(), 500000000 * (10**18))
        self.assertEqual(self.gmt_token.minCap(), 100000000 * (10**18))
        self.assertEqual(self.gmt_token.assignedSupply(), 500000000 * (10**18))
        self.assertEqual(self.gmt_token.saleDuration(), 30)
        self.assertEqual(self.gmt_token.startBlock(), 1467446878)
        self.assertEqual(self.gmt_token.endBlock(), 1470038878)
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
        self.assertEqual(self.gmt_token.balanceOf(self.gmt_multisig_wallet_address), 500000000 * (10**18))
        self.assertEqual(self.gmt_token.balanceOf(self.eth_multisig_wallet_address), 0)

