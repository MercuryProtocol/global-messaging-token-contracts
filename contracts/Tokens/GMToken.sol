pragma solidity 0.4.14;

import 'Tokens/StandardToken.sol';
import 'Utils/SafeMath.sol';

// @title Abstract token contract - Functions to be implemented by token contracts
// @author Preethi Kasireddy - <preethi@preethireddy.com>
contract GMToken is StandardToken {

    using SafeMath for uint256;

    /*
    *  Metadata
    */
    string public constant name = "Global Messaging Token";
    string public constant symbol = "GMT";
    uint256 public constant decimals = 18;

    /*
    *  Contract owner (Radical App International team)
    */
    address public owner;

    /*
    *  Hardware wallets
    // TODO: Add more wallets
    */
    address public ethFundAddress;  // Address for ETH owned by Radical App International
    address public gmtFundAddress;  // Address for GMT allocated to Radical App International
    address public userGrowthFundAddress;  // Address for GMT allocated to user growth pool
    address public employeeAllocationAddress;  // Address for GMT allocated to employees
    address public reservationContractsAddress;  // Address for GMT allocated to reservation contracts

    /*
    *  Crowdsale parameters
    */
    Stages public stage;
    uint256 public startBlock;  // Block number when sale period begins
    uint256 public endBlock;  // Block number when sale period ends
    uint256 public assignedSupply;  // Total GMT tokens currently assigned
    uint256 public constant gmtFund = 500 * (10**6) * 10**decimals;  // 500M GMT reserved for development and user growth fund 
    uint256 public constant tokenExchangeRate = 4316;  // TODO: Units of GMT per ETH
    uint256 public constant minCap = 100 * (10**6) * 10**decimals;  // 100M min cap to be sold during sale

    /*
    *  Events
    */
    event RefundSent(address indexed _to, uint256 _value);
    event CreateGMT(address indexed _to, uint256 _value);

    enum Stages {
        NotStarted,
        InProgress,
        Finalized,
        Failed,
        Stopped
    }

    modifier onlyBy(address _account){
        require(msg.sender == _account);  
        _;
    }

    function changeOwner(address _newOwner) onlyBy(owner) {
        owner = _newOwner;
    }

    modifier minCapReached() {
        assert(assignedSupply - gmtFund >= minCap);
        _;
    }

    modifier respectTimeFrame() {
        assert((block.number >= startBlock) && (block.number < endBlock));
        _;
    }

    modifier salePeriodCompleted() {
        assert(block.number >= endBlock);
        _;
    }

    modifier atStage(Stages _stage) {
        assert(stage == _stage);
        _;
    }

    /*
    *  Constructor
    */
    function GMToken(
        address _ethFundAddress,
        address _gmtFundAddress,
        uint256 _startBlock,
        uint256 _endBlock)
    {
        require(_gmtFundAddress!= 0x0);
        require(_ethFundAddress != 0x0);

        owner = msg.sender; // Creator of contract is owner
        stage = Stages.NotStarted; 
        ethFundAddress = _ethFundAddress;
        gmtFundAddress = _gmtFundAddress;
        startBlock = _startBlock;
        endBlock = _endBlock;
        totalSupply = 1000 * (10**6) * 10**decimals;  // 1B total GMT tokens
        balances[gmtFundAddress] = gmtFund;  // Deposit Radical App International share into Multi-sig
        assignedSupply = gmtFund;  // Set starting assigned supply to amount assigned for GMT fund
        CreateGMT(gmtFundAddress, gmtFund);  // Log Radical App International fund  
    }

    // @notice Start sale
    function startSale() onlyBy(owner) external {
        stage = Stages.InProgress;
    }

    // @notice Stop sale in case of emergency (i.e. circuit breaker)
    function stopSale() onlyBy(owner) external {
        stage = Stages.Stopped;
    }

    // @notice Create `msg.value` ETH worth of GMT
    function createTokens() respectTimeFrame atStage(Stages.InProgress) payable external {
        assert(msg.value > 0);

        // Check that we're not over totals
        uint256 tokens = msg.value.mul(tokenExchangeRate); 
        uint256 checkedSupply = assignedSupply.add(tokens);

        // Return money if we're over total token supply
        assert(checkedSupply <= totalSupply); 

        balances[msg.sender] += tokens;
        assignedSupply = checkedSupply;
        CreateGMT(msg.sender, tokens);  // Logs token creation for UI purposes
    }

    // @notice Ends the funding period and sends the ETH to Multi-sig wallet
    function finalize() 
        onlyBy(owner) 
        atStage(Stages.InProgress) 
        minCapReached 
        salePeriodCompleted
        external
    {
        stage = Stages.Finalized;

        ethFundAddress.transfer(this.balance);
    }

    // @notice Allows contributors to recover their ETH in the case of a failed token sale
    function refund() atStage(Stages.InProgress) salePeriodCompleted external returns (bool) {
        assert(assignedSupply - gmtFund < minCap);  // No refunds if we reached min cap
        assert(msg.sender != gmtFundAddress);  // Radical App International not entitled to a refund

        uint256 gmtVal = balances[msg.sender];
        assert(gmtVal > 0); // Prevent refund if sender GMT balance is 0

        balances[msg.sender] -= gmtVal;
        assignedSupply = assignedSupply.sub(gmtVal); // Adjust assigned supply to account for refunded amount
        
        uint256 ethVal = gmtVal.div(tokenExchangeRate); // Covert GMT to ETH

        stage = Stages.Failed;

        if(!msg.sender.send(ethVal)) {
          // Revert state due to unsuccessful refund
          balances[msg.sender] += gmtVal;
          assignedSupply = assignedSupply.add(gmtVal);
          return false; 
        }
        
        RefundSent(msg.sender, ethVal);  // Log successful refund 
        
        return true;
    }

    /*
        NOTE: We explicitly do not define a fallback function, in order to prevent 
        receiving Ether for no reason. As noted in Solidity documentation, contracts 
        that receive Ether directly (without a function call, i.e. using send or transfer)
        but do not define a fallback function throw an exception, sending back the Ether (this was different before Solidity v0.4.0).
    */
}
