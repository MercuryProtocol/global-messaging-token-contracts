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
        self.assertEqual(self.gmt_token.saleDuration(), 30)
        self.assertEqual(self.gmt_token.tokenExchangeRate(), self.exchangeRate)
        self.assertEqual(self.gmt_token.startBlock(), 1467446878)
        self.assertEqual(self.gmt_token.endBlock(), 1470038878)
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
        self.assertEqual(self.gmt_token.balanceOf(self.gmt_multisig_wallet_address), self.gmtFund)
        self.assertEqual(self.gmt_token.balanceOf(self.eth_multisig_wallet_address), 0)
        self.assertEqual(self.gmt_token.owner(), '0x' + accounts[0].hex())

    def test_create_token_before_sale_starts(self):
        self.assertRaises(TransactionFailed, self.gmt_token.createTokens)

    def test_unauthorized_start_sale(self):
        # Raises if anyone but the owner tries to start the sale
        self.assertRaises(TransactionFailed, self.gmt_token.startSale, sender=keys[3])
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
    
    def test_authorized_start_sale(self):
        self.gmt_token.startSale()
        self.assertEqual(self.gmt_token.stage(), 1) # 1=InProgress

    def test_create_tokens(self):
        self.gmt_token.startSale()
        # Move forward in time
        self.s.block.timestamp += 1

        buyer_1 = 2
        value_1 = 1 * 10**18 # 1 Ether
        buyer_1_tokens = value_1 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), self.gmtFund + buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

    def test_unauthorized_finalize_sale(self):
        self.gmt_token.startSale()
        # Move forward in time
        self.s.block.timestamp += 1
        # Raises if anyone but the owner tries to start the sale
        self.assertRaises(TransactionFailed, self.gmt_token.finalize, sender=keys[3])

    def test_invalid_finalize_sale(self):
        # Raises if try to finalize sale when it's not in progress
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)

    def test_finalize_sale_mincap_not_reached(self):
        self.gmt_token.startSale()
        # Move forward in time
        self.s.block.timestamp += 1


        buyer_1 = 2
        buyer_2 = 3
        buyer_3 = 4
        value_1 = 90 * 10**18 # 90 Ether
        value_2 = 30 * 10**18 # 30 Ether
        value_3 = 200 * 10**18 # 200 Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.createTokens(value=value_3, sender=keys[buyer_3])

        # Should fail when min cap is not reached (i.e. 90 + 20 + 200 < minCap / exchangeRate)
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)
    
    def test_finalize_sale(self):
        self.gmt_token.startSale()
        # Move forward in time
        self.s.block.timestamp += 1


        buyer_1 = 2
        buyer_2 = 3
        buyer_3 = 4
        value_1 = 900 * 10**18 # 90 Ether
        value_2 = 30000 * 10**18 # 30 Ether
        value_3 = 200 * 10**18 # 200 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens = value_2 * self.exchangeRate
        buyer_3_tokens = value_3 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.createTokens(value=value_3, sender=keys[buyer_3])

        # Should work when min cap is reached (i.e. 900 + 30000 + 200 >= minCap / exchangeRate)
        self.gmt_token.finalize()
        self.assertEqual(self.gmt_token.stage(), 2) # 2=Finalized
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_2]), buyer_2_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_3]), buyer_3_tokens)

        # TODO: figure out why this balance is 0
        # self.assertEqual(self.gmt_token.balanceOf(self.eth_multisig_wallet_address), value_1)

    # TODO: Add tests for Refund function