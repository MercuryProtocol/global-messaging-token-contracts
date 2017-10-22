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
        self.exchangeRate = 5000
        self.saleDuration = round((30*60*60*24)/18)
        self.endBlock = self.startBlock + self.saleDuration
        self.gmt_token= self.create_contract('Tokens/GMTokenFlattened.sol',
                                                args=(self.eth_wallet_address,
                                                self.gmt_wallet_address,
                                                self.startBlock,
                                                self.endBlock,
                                                self.exchangeRate))
        self.owner = self.gmt_token.owner()
        self.gmtFund = 500000000 * (10**18)
        self.totalSupply = 1000000000 * (10**18)
        self.m = 4316
        

    def test_meta_data(self):
        self.assertEqual(self.gmt_token.name().decode(), "Global Messaging Token")
        self.assertEqual(self.gmt_token.symbol().decode(), "GMT")
        self.assertEqual(self.gmt_token.decimals(), 18)

    def test_initial_state(self):
        self.assertEqual(self.gmt_token.totalSupply(), self.totalSupply)
        self.assertEqual(self.gmt_token.gmtFund(), self.gmtFund)
        self.assertEqual(self.gmt_token.minCap(), 100000000 * (10**18))
        self.assertEqual(self.gmt_token.assignedSupply(), 0)
        self.assertEqual(self.gmt_token.tokenExchangeRate(), self.exchangeRate)
        self.assertEqual(self.gmt_token.startBlock(), self.startBlock)
        self.assertEqual(self.gmt_token.endBlock(), self.endBlock)
        self.assertEqual(self.gmt_token.firstCapEndingBlock(), self.startBlock + self.gmt_token.blocksInFirstCapPeriod())
        self.assertEqual(self.gmt_token.secondCapEndingBlock(), self.startBlock + self.gmt_token.blocksInFirstCapPeriod() + self.gmt_token.blocksInSecondCapPeriod())
        self.assertEqual(self.gmt_token.baseTokenCapPerAddress(), self.exchangeRate * self.gmt_token.baseEthCapPerAddress())
        self.assertEqual(self.gmt_token.isFinalized(), False)
        self.assertEqual(self.gmt_token.isStopped(), False)
        self.assertEqual(self.gmt_token.owner(), '0x' + accounts[0].hex())

    def test_create_token_before_sale_starts(self):
        self.c.head_state.block_number = self.startBlock - 1
        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether
        buyer_1_tokens = value_1 * self.exchangeRate

        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1, sender=keys[buyer_1])

    def test_unauthorized_stop_sale(self): # circuit breaker
        # Raises if anyone but the owner tries to start the sale
        self.assertRaises(TransactionFailed, self.gmt_token.stopSale, sender=keys[3])

    def test_unauthorized_restart_sale(self):
        # Raises if anyone but the owner tries to start the sale
        self.assertRaises(TransactionFailed, self.gmt_token.restartSale, sender=keys[3])
    
    def test_authorized_stop_sale(self):
        # NOTE: owner is account[0] because that is what 
        # the default sender gets set to with pyethereum when not explicitly indicated
        self.gmt_token.stopSale() 
        self.assertEqual(self.gmt_token.isStopped(), True)

    def test_authorized_restart_sale(self):
        self.gmt_token.restartSale() 
        self.assertEqual(self.gmt_token.isStopped(), False)

    def test_change_registration_status_unauthorized(self):
        participant_1 = 3
        self.assertRaises(TransactionFailed, self.gmt_token.changeRegistrationStatus, accounts[participant_1], True, sender=keys[3])

    def test_change_registration_status_authorized(self):
        participant_1 = 7
        self.gmt_token.changeRegistrationStatus(accounts[participant_1], True)
        self.assertEqual(self.gmt_token.registered(accounts[participant_1]), True)

    def test_change_registration_statuses_unauthorized(self):
        participant_1 = 3
        participant_2 = 4
        participant_3 = 5
        targets = [accounts[participant_1], accounts[participant_2], accounts[participant_3]]
        self.assertRaises(TransactionFailed, self.gmt_token.changeRegistrationStatuses, targets, True, sender=keys[7])

    def test_change_registration_statuses_authorized(self):
        participant_1 = 3
        participant_2 = 4
        participant_3 = 5
        targets = [accounts[participant_1], accounts[participant_2], accounts[participant_3]]
        self.gmt_token.changeRegistrationStatuses(targets, True)
        self.assertEqual(self.gmt_token.registered(accounts[participant_1]), True)
        self.assertEqual(self.gmt_token.registered(accounts[participant_2]), True)
        self.assertEqual(self.gmt_token.registered(accounts[participant_3]), True)

    def test_create_tokens_more_than_total_supply(self):
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 4000

        buyer_1 = 3
        value_1 = 100000 * 10**18 # 100K Ether
        buyer_2 = 4
        value_2_incorrect = 20000 * 10**18 # 20K Ether
        targets = [accounts[buyer_1], accounts[buyer_2]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens_too_many = value_2_incorrect * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2_incorrect * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_2_incorrect, sender=keys[3])

    def test_create_tokens_zero_value(self):
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 1000

        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether

        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=0, sender=keys[buyer_1])
    
    def test_create_tokens_unregistered(self):
        # Move forward a few blocks to be within funding time frame
        self.c.head_state.block_number = self.startBlock + 1000

        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether
        buyer_1_tokens = value_1 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1, sender=keys[buyer_1])

    def test_create_tokens_more_than_first_individual_cap(self):
        # Move forward a few blocks to be within funding time frame AND within first individual cap period
        self.c.head_state.block_number = self.gmt_token.firstCapEndingBlock() - 10

        buyer_1 = 3
        value_1 = 11 * 10**18 # 11 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1, sender=keys[buyer_1])

    def test_create_tokens_more_than_second_individual_cap(self):
        # Move forward a few blocks to be within funding time frame AND within second individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() - 10

        buyer_1 = 3
        value_1 = 51 * 10**18 # 1 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1, sender=keys[buyer_1])

    def test_create_tokens_under_first_and_second_individual_cap(self):
        # Move forward a few blocks to be within funding time frame AND within second individual cap period
        self.c.head_state.block_number = self.gmt_token.firstCapEndingBlock() - 10

        buyer_1 = 3
        value_1 = 5 * 10**18 # 5 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() - 10

        # Buyer buys again during second period, but more than allowed
        value_1_more = 40 * 10**18 # 1 Ether
        buyer_1_tokens_more = value_1 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1_more * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1_more, sender=keys[buyer_1])
        
        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

    def test_create_tokens_under_first_individual_cap(self):
        # Move forward a few blocks to be within funding time frame AND within first individual cap period
        self.c.head_state.block_number = self.gmt_token.firstCapEndingBlock() - 10

        buyer_1 = 4
        value_1 = 6 * 10**18 # 6 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)
    
    def test_create_tokens_under_second_individual_cap(self):
        # Move forward a few blocks to be within funding time frame AND within second individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() - 10

        buyer_1 = 4
        value_1 = 27 * 10**18 # 27 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

    def test_create_tokens_then_transfer_to_another_account(self):
        # Move forward a few blocks to be within funding time frame AND within first individual cap period
        self.c.head_state.block_number = self.gmt_token.firstCapEndingBlock() - 10

        buyer_1 = 4
        value_1 = 6 * 10**18 # 6 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

        self.gmt_token.transfer("0xd6189c09b3708cee1d35d00de32b02abc7fbd55d", buyer_1_tokens, sender=keys[buyer_1])
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), 0)
        
        # Buyer tries to buy again during cap period, but more than allowed for this cap period
        value_1_more = 5 * 10**18 # 1 Ether
        buyer_1_tokens_more = value_1 * self.exchangeRate

        self.c.head_state.set_balance(accounts[buyer_1], value_1_more * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1_more, sender=keys[buyer_1])


    def test_create_tokens_over_gas_limit(self):
        # Move forward a few blocks to be within funding time frame AND within first individual cap period
        self.c.head_state.block_number = self.gmt_token.firstCapEndingBlock() - 1
        
        buyer_1 = 4
        value_1 = 6 * 10**18 # 6 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        # Pyethereum Tester module not passing through gasprice for some reason?
        # self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, value=value_1, sender=keys[buyer_1], gasprice=52000000000)

    def test_create_tokens(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])

        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)

    def test_buying_after_circuit_breaker(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1
        self.gmt_token.stopSale()
        # Raises if try to finalize sale when it's not in progress
        self.assertEqual(self.gmt_token.isStopped(), True)

        buyer_1 = 3
        value_1 = 1 * 10**18 # 1 Ether
        # Register user for participation
        self.gmt_token.changeRegistrationStatus(accounts[buyer_1], True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.assertRaises(TransactionFailed, self.gmt_token.claimTokens, sender=keys[buyer_1])
    
    def test_finalize_before_endTime(self):
        # Raises if try to finalize before sale period is over
        self.assertTrue(self.c.head_state.block_number < self.endBlock) 
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)

    def test_unauthorized_finalize(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        buyer_3 = 5
        value_1 = 90 * 10**18 # 90 Ether
        value_2 = 30000 * 10**18 # 30k Ether
        value_3 = 200 * 10**18 # 200 Ether
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2], accounts[buyer_3]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.claimTokens(value=value_3, sender=keys[buyer_3])

         # Set block number to past endBlock to allow finalize
        self.c.head_state.block_number = self.endBlock + 1

        # Raises if anyone but the owner tries to finalize the sale
        self.assertRaises(TransactionFailed, self.gmt_token.finalize, sender=keys[3])

    def test_finalize_mincap_not_reached(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        buyer_3 = 5
        value_1 = 90 * 10**18 # 90 Ether
        value_2 = 30 * 10**18 # 30 Ether
        value_3 = 200 * 10**18 # 200 Ether
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2], accounts[buyer_3]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.claimTokens(value=value_3, sender=keys[buyer_3])

         # Set block number to past endBlock to allow finalize
        self.c.head_state.block_number = self.endBlock + 1

        # Should fail when min cap is not reached (i.e. 90 + 30 + 200 < minCap / exchangeRate)
        self.assertRaises(TransactionFailed, self.gmt_token.finalize)
    
    def test_finalize_after_mincap_before_sale_period(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        buyer_3 = 5
        value_1 = 10000 * 10**18 # 10k Ether
        value_2 = 20000 * 10**18 # 20k Ether
        value_3 = (1 * 10**23) - value_1 - value_2 # Remaining supply = (500M tokens / exchangeRate) - (already assigned supply)

        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2], accounts[buyer_3]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens = value_2 * self.exchangeRate
        buyer_3_tokens = value_3 * self.exchangeRate
        starting_balance = self.c.head_state.get_balance(self.eth_wallet_address)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)

        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.claimTokens(value=value_3, sender=keys[buyer_3])

         # Verify we've updated the total assigned supply of GMT appropriately
        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens + buyer_2_tokens + buyer_3_tokens)

        # Set block number to before end block
        self.c.head_state.block_number = self.endBlock - 10
        # Should work when assigned supply is total supply
        self.gmt_token.finalize()
        self.assertEqual(self.gmt_token.isFinalized(), True)

        # Verify buyers received the appropriate token amount
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_2]), buyer_2_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_3]), buyer_3_tokens)

        # Verify GMT funds were sent to GMT fund address
        self.assertEqual(self.gmt_token.balanceOf(self.gmt_wallet_address), self.gmt_token.gmtFund())

        # Verify we've updated the total assigned supply of GMT to account for unassigned supply being sent to GMT fund
        self.assertEqual(self.gmt_token.assignedSupply(), self.gmt_token.totalSupply())

        # Verify ETH balance of ETH wallet address
        self.assertEqual(round(self.c.head_state.get_balance(self.eth_wallet_address), -10), value_1 + value_2 + value_3 + starting_balance)
    
    def test_finalize(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        buyer_3 = 5
        value_1 = 900 * 10**18 # 900 Ether
        value_2 = 30000 * 10**18 # 30k Ether
        value_3 = 200 * 10**18 # 200 Ether
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2], accounts[buyer_3]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens = value_2 * self.exchangeRate
        buyer_3_tokens = value_3 * self.exchangeRate
        starting_balance = self.c.head_state.get_balance(self.eth_wallet_address)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        self.c.head_state.set_balance(accounts[buyer_3], value_3 * 2)
        
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])
        self.gmt_token.claimTokens(value=value_3, sender=keys[buyer_3])

        # Verify we've updated the total assigned supply of GMT appropriately
        self.assertEqual(self.gmt_token.assignedSupply(), buyer_1_tokens + buyer_2_tokens + buyer_3_tokens)

        # Set block number to past endBlock to allow finalize
        self.c.head_state.block_number = self.endBlock + 1

        # Calculate the unassigned supply
        unassignedSupply = self.gmt_token.totalSupply() - self.gmt_token.assignedSupply() - self.gmt_token.gmtFund()
        
        # Should work when min cap is reached (i.e. 900 + 30000 + 200 >= minCap / exchangeRate)
        self.gmt_token.finalize()
        self.assertEqual(self.gmt_token.isFinalized(), True)

        # Verify buyers received the appropriate token amount
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), buyer_1_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_2]), buyer_2_tokens)
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_3]), buyer_3_tokens)

        # Verify GMT funds were sent to GMT fund address, and any unassigned supply
        self.assertEqual(self.gmt_token.balanceOf(self.gmt_wallet_address), self.gmt_token.gmtFund() + unassignedSupply)

        # Verify we've updated the total assigned supply of GMT to account for unassigned supply being sent to GMT fund
        self.assertEqual(self.gmt_token.assignedSupply(), self.totalSupply)

        # Verify ETH balance of ETH wallet address
        self.assertEqual(round(self.c.head_state.get_balance(self.eth_wallet_address), -10), value_1 + value_2 + value_3 + starting_balance)
    
    def test_refund_after_finalized(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30000 * 10**18 # 30k Ether
        value_2 = 5000 * 10**18 # 5k Ether
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        self.gmt_token.finalize()
        self.assertEqual(self.gmt_token.isFinalized(), True)

        # Raises if contributor tries to get a refund after sale is finalized
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[buyer_1])

    def test_refund_after_mincap_reached(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 1300 * 10**18 # 1300 Ether
        value_2 = 30000 * 10**18 # 30k Ether
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        self.assertEqual(self.gmt_token.isFinalized(), False)

        # Raises if contributor tries to get a refund after min cap is reached
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[buyer_1])
    
    def test_refund_for_gmtFund(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether
        # Register user for participation
        targets = [accounts[buyer_1], accounts[buyer_2]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        self.assertEqual(self.gmt_token.isFinalized(), False)

        # Raises if gmtFund address tries to get a refund (account[1])
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[1])

    def test_refund_when_sender_balance_zero(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        # Contributor buyer_1 asks for refund
        self.gmt_token.refund(sender=keys[buyer_1], value=0)

        # Raises if sender balance is 0 but tries to ask for refund
        buyer_3 = 5
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_3]), 0)
        self.assertRaises(TransactionFailed, self.gmt_token.refund, sender=keys[buyer_3])

    def test_refund(self):
        # Move forward a few blocks to be within funding time frame AFTER individual cap period
        self.c.head_state.block_number = self.gmt_token.secondCapEndingBlock() + 1

        buyer_1 = 3
        buyer_2 = 4
        value_1 = 30 * 10**18 # 30 Ether
        value_2 = 10 * 10**18 # 10 Ether
        buyer_1_tokens = value_1 * self.exchangeRate
        buyer_2_tokens = value_2 * self.exchangeRate
        # Register users for participation
        targets = [accounts[buyer_1], accounts[buyer_2]]
        self.gmt_token.changeRegistrationStatuses(targets, True)

        self.c.head_state.set_balance(accounts[buyer_1], value_1 * 2)
        self.c.head_state.set_balance(accounts[buyer_2], value_2 * 2)
        
        self.gmt_token.claimTokens(value=value_1, sender=keys[buyer_1])
        self.gmt_token.claimTokens(value=value_2, sender=keys[buyer_2])

        # Set block number to past endBlock to allow refund
        self.c.head_state.block_number = self.endBlock + 1

        # Contributor buyer_1 asks for refund
        self.gmt_token.refund(sender=keys[buyer_1], value=0)

        # Ensure buyer_1 is refunded
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_1]), 0)

        # Update assigned supply of GMT appropriately to account for buyer_1 refund
        self.assertEqual(self.gmt_token.assignedSupply(), buyer_2_tokens)

        # Contributor buyer_2 asks for refund
        self.gmt_token.refund(sender=keys[buyer_2], value=0)

        # Ensure buyer_1 is refunded
        self.assertEqual(self.gmt_token.balanceOf(accounts[buyer_2]), 0)

        # Update assigned supply of GMT appropriately to account for buyer_1 & buyer_2 refund
        self.assertEqual(self.gmt_token.assignedSupply(), 0)
