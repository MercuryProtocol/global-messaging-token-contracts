from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.tokens.test_gmt_token
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)

    def test_initial_state(self):
        eth_multisig_wallet_address = accounts[0]
        gmt_multisig_wallet_address = accounts[1]
        self.gmt_token= self.create_contract('Tokens/GMTokenAll.sol',
                                                args=(eth_multisig_wallet_address, gmt_multisig_wallet_address))
        self.assertEqual(self.gmt_token.name().decode(), "Global Messaging Token")
        self.assertEqual(self.gmt_token.symbol().decode(), "GMT")
        self.assertEqual(self.gmt_token.decimals(), 18)
        self.assertEqual(self.gmt_token.totalSupply(), 1000000000 * (10**18))
        self.assertEqual(self.gmt_token.gmtFund(), 500000000 * (10**18))
        self.assertEqual(self.gmt_token.minCap(), 100000000 * (10**18))
        self.assertEqual(self.gmt_token.assignedSupply(), 500000000 * (10**18))
        self.assertEqual(self.gmt_token.saleDuration(), 30)
        self.assertEqual(self.gmt_token.startBlock(), 1467446878)
        self.assertEqual(self.gmt_token.endBlock(), 1470038878)
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
        self.assertEqual(self.gmt_token.balanceOf(gmt_multisig_wallet_address), 500000000 * (10**18))
        self.assertEqual(self.gmt_token.balanceOf(eth_multisig_wallet_address), 0)

