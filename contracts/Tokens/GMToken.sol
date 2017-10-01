pragma solidity 0.4.15;

import 'contracts/Tokens/StandardToken.sol';
import 'contracts/Utils/SafeMath.sol';

/// @title GMT Token - Main token sale contract
/// @author Preethi Kasireddy - <preethi@preethireddy.com>

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
    */
    address public ethFundAddress;  // Address for ETH owned by Radical App International
    address public gmtFundAddress;  // Address for GMT allocated to Radical App International

    /*
    *  List of registered participants
    */
    mapping (address => bool) public registered;

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
    event ClaimGMT(address indexed _to, uint256 _value);

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

    modifier registeredUser() {
        require(registered[msg.sender] == true);  
        _;
    }

    modifier minCapReached() {
        require(assignedSupply - gmtFund >= minCap);
        _;
    }

    modifier respectTimeFrame() {
        require((block.number >= startBlock) && (block.number < endBlock));
        _;
    }

    modifier salePeriodCompleted() {
        require(block.number >= endBlock);
        _;
    }

    modifier atStage(Stages _stage) {
        require(stage == _stage);
        _;
    }

    /*
    *  Constructor
    */
    function GMToken(
        address _ethFundAddress,
        address _gmtFundAddress,
        uint256 _startBlock,
        uint256 _endBlock) {
        require(_gmtFundAddress != 0x0);
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
        ClaimGMT(gmtFundAddress, gmtFund);  // Log Radical App International fund
        // As per ERC20 spec, a token contract which creates new tokens SHOULD trigger a Transfer event with the _from address
        // set to 0x0 when tokens are created (https://github.com/ethereum/EIPs/blob/master/EIPS/eip-20-token-standard.md)
        Transfer(0x0, gmtFundAddress, gmtFund);
    }

    /// @notice Start sale
    /// @dev Only allowed to be called by the owner
    function startSale() onlyBy(owner) external {
        stage = Stages.InProgress;
    }

    /// @notice Stop sale in case of emergency (i.e. circuit breaker)
    /// @dev Only allowed to be called by the owner
    function stopSale() onlyBy(owner) external {
        stage = Stages.Stopped;
    }

    /// @notice Set sale to failed state
    /// @dev Only allowed to be called by the owner
    function setFailedState() onlyBy(owner) external {
        stage = Stages.Failed;
    }

    /// @notice Create `msg.value` ETH worth of GMT
    /// @dev Only allowed to be called within the timeframe of the sale period
    function claimTokens() respectTimeFrame registeredUser atStage(Stages.InProgress) payable external {
        require(msg.value > 0);

        // Check that we're not over totals
        uint256 tokens = msg.value.mul(tokenExchangeRate); 
        uint256 checkedSupply = assignedSupply.add(tokens);

        // Return money if we're over total token supply
        require(checkedSupply <= totalSupply); 

        balances[msg.sender] += tokens;
        assignedSupply = checkedSupply;
        ClaimGMT(msg.sender, tokens);  // Logs token creation for UI purposes
    }


    /// @notice Updates registration status of an address for sale participation
    /// @param target Address that will be registered or deregistered
    /// @param isRegistered New registration status of address
    function changeRegistrationStatus(address target, bool isRegistered) public onlyBy(owner) {
        registered[target] = isRegistered;
    }

    /// @notice Updates registration status for multiple addresses for participation
    /// @param targets Addresses that will be registered or deregistered
    /// @param isRegistered New registration status of addresses
    function changeRegistrationStatuses(address[] targets, bool isRegistered) public onlyBy(owner) {
        for (uint i = 0; i < targets.length; i++) {
            changeRegistrationStatus(targets[i], isRegistered);
        }
    }

    /// @notice Ends the funding period and sends the ETH to Multi-sig wallet
    /// @dev Only allowed to be called by the owner once sale period is over and the min cap is reached
    function finalize() 
        onlyBy(owner) 
        atStage(Stages.InProgress) 
        minCapReached 
        salePeriodCompleted
        external
    {
        stage = Stages.Finalized;

        // In the case where not all 500M GMT allocated to crowdfund participants
        // is sold, send the remaining unassigned supply to GMT fund address,
        // which will then be used to fund the user growth pool.
        if (assignedSupply < totalSupply) {
            uint256 unassignedSupply = totalSupply.sub(assignedSupply);
            balances[gmtFundAddress] += unassignedSupply;
            assignedSupply = assignedSupply.add(unassignedSupply);
        }

        ethFundAddress.transfer(this.balance);
    }

    /// @notice Allows contributors to recover their ETH in the case of a failed token sale
    /// @dev Only allowed to be called once sale period is over IF the min cap is not reached
    /// @return bool True if refund successfully sent, false otherwise
    function refund() registeredUser atStage(Stages.Failed) salePeriodCompleted external returns (bool) {
        require(assignedSupply - gmtFund < minCap);  // No refunds if we reached min cap
        require(msg.sender != gmtFundAddress);  // Radical App International not entitled to a refund

        uint256 gmtVal = balances[msg.sender];
        require(gmtVal > 0); // Prevent refund if sender GMT balance is 0

        balances[msg.sender] -= gmtVal;
        assignedSupply = assignedSupply.sub(gmtVal); // Adjust assigned supply to account for refunded amount
        
        uint256 ethVal = gmtVal.div(tokenExchangeRate); // Covert GMT to ETH

        msg.sender.transfer(ethVal);
        
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
