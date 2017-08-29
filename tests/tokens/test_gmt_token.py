from ..abstract_test import AbstractTestContracts, accounts, keys, TransactionFailed
from ethereum.tools import tester
from ethereum.utils import privtoaddr

class TestContract(AbstractTestContracts):
    """
    run test with python -m unittest tests.tokens.test_gmt_token
    """

    def __init__(self, *args, **kwargs):
        super(TestContract, self).__init__(*args, **kwargs)
        # NOTE: balances default to 1 ETH
        self.gmt_wallet_address = accounts[1]
        self.eth_wallet_address = accounts[2]
        self.startBlock = 4097906
        self.saleDuration = round((30*60*60*24)/18)
        self.endBlock = self.startBlock + self.saleDuration
        self.gmt_token= self.create_contract('Tokens/GMTokenFlattened.sol',
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

    def test_create_token_before_sale_starts(self):
        self.assertRaises(TransactionFailed, self.gmt_token.createTokens)

    def test_unauthorized_start(self):
        # Raises if anyone but the owner tries to start the sale
        self.assertRaises(TransactionFailed, self.gmt_token.startSale, sender=keys[3])
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
    
    def test_authorized_start(self):
        # NOTE: owner is account[0] because that is what 
        # the default sender gets set to with pyethereum when not explicitly indicated
        self.gmt_token.startSale() 
        self.assertEqual(self.gmt_token.stage(), 1) # 1=InProgress

    def test_create_tokens(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether
        buyer_1_tokens = value_1 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), self.gmtFund + buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

    def test_circuit_breaker(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100
        self.gmt_token.stopSale()
        # Raises if try to finalize sale when it's not in progress
        self.assertEqual(self.gmt_token.stage(), 4) # 4=Failed

        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.createTokens, sender=keys[buyer_1])

    def test_invalid_finalize(self):
        # Raises if try to finalize sale when it's not in progress
        self.assertEqual(self.gmt_token.stage(), 0) # 0=NotStarted
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)
    
    def test_finalize_before_endTime(self):
        self.gmt_token.startSale()
        # Raises if try to finalize before sale period is over
        self.assertTrue(self.c.head_state.block_number < self.endBlock) 
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)

    def test_unauthorized_finalize(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100
        # Raises if anyone but the owner tries to finalize the sale
        self.assertRaises(TransactionFailed, self.gmt_token.finalize, sender=keys[3])

    def test_finalize_mincap_not_reached(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        buyer_3 = 5
        value_1 = 90 * 10**18 # 90 Ether
        value_2 = 30 * 10**18 # 30 Ether
        value_3 = 200 * 10**18 # 200 Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.createTokens(value=value_3, sender=keys[buyer_3])

         # Set block number to past endBlock to allow finalize
        self.c.head_state.block_number = self.endBlock + 1

        # Should fail when min cap is not reached (i.e. 90 + 30 + 200 < minCap / exchangeRate)
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)
    
    def test_finalize(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        buyer_3 = 5
        value_1 = 900 * 10**18 # 90 Ether
        value_2 = 30000 * 10**18 # 30k Ether
        value_3 = 200 * 10**18 # 200 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens = value_2 * self.exchangeRate
        buyer_3_tokens = value_3 * self.exchangeRate
        starting_balance = self.c.head_state.get_balance(self.eth_wallet_address)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.createTokens(value=value_3, sender=keys[buyer_3])

        # Verify we've updated the total assigned supply of GMT appropriately
        self.assertEqual(self.gmt_token.assignedSupply(), self.gmtFund + buyer_1_tokens + buyer_2_tokens + buyer_3_tokens)

        # Calculate the unassigned supply
        unassignedSupply = self.gmt_token.totalSupply() - self.gmt_token.assignedSupply()

        # Set block number to past endBlock to allow finalize
        self.c.head_state.block_number = self.endBlock + 1
        
        # Should work when min cap is reached (i.e. 900 + 30000 + 200 >= minCap / exchangeRate)
        self.gmt_token.finalize()
        self.assertEqual(self.gmt_token.stage(), 2) # 2=Finalized

        # Verify buyers received the appropriate token amount
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_2]), buyer_2_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_3]), buyer_3_tokens)

        # Verify we've updated the total supply of GMT to account for unassigned supply
        self.assertEqual(self.gmt_token.assignedSupply(), self.totalSupply)
        self.assertEqual(self.gmt_token.balanceOf(self.gmt_wallet_address), self.gmtFund + unassignedSupply)

        # Verify ETH balance of ETH wallet address
        self.assertEqual(round(self.c.head_state.get_balance(self.eth_wallet_address), -10), value_1 + value_2 + value_3 + starting_balance)
    
    def test_refund_while_sale_in_progress(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        self.assertEqual(self.gmt_token.stage(), 1) # 1=InProgress

        # Raises if contributor tries to get a refund after min cap is reached
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[buyer_1])

    def test_refund_after_mincap_reached(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 1300 * 10**18 # 1300 Ether
        value_2 = 30000 * 10**18 # 30k Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        # Owner needs to set sale to failed state to allow refunds to process
        self.gmt_token.setFailedState()

        self.assertEqual(self.gmt_token.stage(), 3) # 3=Failed

        # Raises if contributor tries to get a refund after min cap is reached
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[buyer_1])
    
    def test_refund_for_gmtFund(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        # Owner needs to set sale to failed state to allow refunds to process
        self.gmt_token.setFailedState()

        self.assertEqual(self.gmt_token.stage(), 3) # 3=Failed

        # Raises if gmtFund address tries to get a refund (account[1])
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[1])

    def test_refund_when_sender_balance_zero(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        # Owner needs to set sale to failed state to allow refunds to process
        self.gmt_token.setFailedState()

        self.assertEqual(self.gmt_token.stage(), 3) # 3=Failed

        # Raises if sender balance is 0
        buyer_3 = 5
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_3]), 0)
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[buyer_3])

    def test_refund(self):
        self.gmt_token.startSale()
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 100

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens = value_2 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.createTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.createTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        # Owner needs to set sale to failed state to allow refunds to process
        self.gmt_token.setFailedState()

        self.assertEqual(self.gmt_token.stage(), 3) # 3=Failed

        # Contributor buyer_1 asks for refund
        self.gmt_token.refund(sender=keys[buyer_1], value=0)

        # Ensure buyer_1 is refunded
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), 0)

        # Update assigned supply of GMT appropriately to account for buyer_1 refund
        self.assertEqual(self.gmt_token.assignedSupply(), self.gmtFund + buyer_2_tokens)

        # Contributor buyer_2 asks for refund
        self.gmt_token.refund(sender=keys[buyer_2], value=0)

        # Ensure buyer_1 is refunded
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_2]), 0)

        # Update assigned supply of GMT appropriately to account for buyer_1 & buyer_2 refund
        self.assertEqual(self.gmt_token.assignedSupply(), self.gmtFund)
