from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed
from ethereum.tools import tester
from ethereum.utils import privtoaddr

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.tokens.test_gmt_safe
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)
        # NOTE: multisig balances default to 1 ETH
        self.gmt_wallet_address = accounts[1]
        self.eth_wallet_address = accounts[2]
        self.startBlock = 4097906
        self.saleDuration = round((30*60*60*24)/18)
        self.endBlock = self.startBlock + self.saleDuration
        self.gmt_token= self.create_contract('Tokens/GMTokenTestFile.sol',
                                                args=(self.eth_wallet_address,
                                                self.gmt_wallet_address,
                                                self.startBlock,
                                                self.endBlock))
        self.owner = self.gmt_token.owner()
        self.gmtFund = 500000000 * (10**18)
        self.totalSupply = 1000000000 * (10**18)
        self.exchangeRate = 4316
        

    def test_meta_data(self):
        self.assertEqual(self.gmt_token.name().decode(), "Global Messaging Token")
        self.assertEqual(self.gmt_token.symbol().decode(), "GMT")
        self.assertEqual(self.gmt_token.decimals(), 18)

    def test_initial_state(self):
        self.assertEqual(self.gmt_token.totalSupply(), self.totalSupply)
        self.assertEqual(self.gmt_token.gmtFund(), self.gmtFund)
        self.assertEqual(self.gmt_token.minCap(), 100000000 * (10**18))
        self.assertEqual(self.gmt_token.assignedSupply(), self.gmtFund)
        self.assertEqual(self.gmt_token.tokenExchangeRate(), self.exchangeRate)
        self.assertEqual(self.gmt_token.startBlock(), self.startBlock)
        self.assertEqual(self.gmt_token.endBlock(), self.endBlock)
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
        self.assertEqual(self.gmt_token.balanceOf(self.gmt_wallet_address), self.gmtFund)
        self.assertEqual(self.gmt_token.owner(), '0x' + accounts[0].hex())