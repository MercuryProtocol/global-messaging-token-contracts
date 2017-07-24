from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.tokens.test_gmt_token
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)

    def test(self):
        eth_multisig_wallet_address = accounts[0]
        gmt_multisig_wallet_address = accounts[1]
        self.gmt_token= self.create_contract_2('Tokens/GMTokenAll.sol',
                                                args=(eth_multisig_wallet_address, gmt_multisig_wallet_address))
        self.assertEqual(self.gmt_token.name().decode(), "Global Messaging Token")
        self.assertEqual(self.gmt_token.symbol().decode(), "GMT")
        self.assertEqual(self.gmt_token.version().decode(), "1.0")
        self.assertEqual(self.gmt_token.decimals(), 18)

