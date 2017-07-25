pragma solidity ^0.4.11;

import "./StandardToken.sol";
import './Utils/SafeMath.sol';

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
    *  Multi-sig wallets
    */
    address public ethFundMultiSig;  // Multi-sig address for ETH owned by Radical App International
    address public gmtFundMultiSig;  // Multi-sig address for GMT allocated to Radical App International

    /*
    *  Crowdsale parameters
    */
    Stages public stage;
    uint256 public startBlock;
    uint256 public endBlock;
    uint256 public assignedSupply;  // Total GMT tokens currently assigned
    uint256 public constant gmtFund = 500 * (10**6) * 10**decimals;  // 500M GMT reserved for development and user growth fund 
    uint256 public constant tokenExchangeRate = 4316;  // TODO: Units of GMT per ETH
    uint256 public constant minCap =  100 * (10**6) * 10**decimals;  // 100M min cap for GMT tokens
    uint256 public constant saleDuration =  30;  // 30 days sale period

    /*
    *  Events
    */
    event RefundSent(address indexed _to, uint256 _value);
    event CreateGMT(address indexed _to, uint256 _value);

    enum Stages {
        NotStarted,
        InProgress,
        Finalized,
        Failed
    }

    modifier onlyBy(address _account){
        require(msg.sender == _account);  
        _;
    }

    function changeOwner(address _newOwner) onlyBy(owner) {
        owner = _newOwner;
    }

    modifier minCapReached() {
        assert((now > endBlock) || ((assignedSupply - gmtFund) >= minCap));
        _;
    }

    modifier respectTimeFrame() {
        assert((now >= startBlock) && (now < endBlock));
        _;
    }

    modifier atStage(Stages _stage) {
        assert(stage == _stage);
        _;
    }

    // TODO: See if we want to consider ownable and pausable contracts? https://github.com/iExecBlockchainComputing/rlc-token/blob/master/contracts/Ownable.sol
    // TODO: Evaluate code using
      // - https://github.com/melonproject/oyente
      // - https://github.com/sc-forks/solidity-coverage
      // - 
    /*
    *  Constructor
    */
    function GMToken(address _ethFundMultiSig, address _gmtFundMultiSig) {
        require(_gmtFundMultiSig != 0x0);
        require(_ethFundMultiSig != 0x0);

        owner = msg.sender;
        stage = Stages.NotStarted;  // Controls pre through crowdsale state
        ethFundMultiSig = _ethFundMultiSig;
        gmtFundMultiSig = _gmtFundMultiSig;
        startBlock = now;
        endBlock = now + (saleDuration * 1 days);
        totalSupply = 1000 * (10**6) * 10**decimals;  // 1B total GMT tokens
        balances[gmtFundMultiSig] = gmtFund;  // Deposit Radical App International share into Multi-sig
        assignedSupply = gmtFund;  // Start assigned supply with reserved GMT fund amount
        CreateGMT(gmtFundMultiSig, gmtFund);  // Log Radical App International fund  
    }

    function startSale() onlyBy(owner) {
        stage = Stages.InProgress;
    }

    // @notice Create `msg.value` ETH worth of GMT
    // TODO: make this the default function?
    function createTokens() respectTimeFrame atStage(Stages.InProgress) payable external {
        assert(msg.value > 0);

        // Check that we're not over totals
        uint256 tokens = msg.value.mul(tokenExchangeRate); 
        uint256 checkedSupply = assignedSupply.add(tokens);

        // Return money if reached token supply
        assert(checkedSupply <= totalSupply); 

        balances[msg.sender] += tokens;
        assignedSupply = checkedSupply;
        CreateGMT(msg.sender, tokens);  // Logs token creation for UI purposes
    }

    // @notice Ends the funding period and sends the ETH to Multi-sig wallet
    function finalize() onlyBy(owner) atStage(Stages.InProgress) minCapReached external {
        stage = Stages.Finalized;

        ethFundMultiSig.send(this.balance);
    }

    // @notice Allows contributors to recover their ETH in the case of a failed funding campaign
    function refund() onlyBy(owner) atStage(Stages.InProgress) external returns (bool) {
        assert(assignedSupply < minCap);  // No refunds if we sold enough
        assert(block.number > endBlock);  // prevents refund until sale period is over
        assert(msg.sender != gmtFundMultiSig);  // Radical App International not entitled to a refund

        uint256 gmtVal = balances[msg.sender];
        require(gmtVal > 0); // Prevent refund if sender balance is 0

        balances[msg.sender] -= gmtVal;
        assignedSupply = assignedSupply.sub(gmtVal);
        
        uint256 ethVal = gmtVal.div(tokenExchangeRate);
        
        if(!msg.sender.send(ethVal)) {
          // revert state due to unsuccessful refund
          balances[msg.sender] += gmtVal;
          assignedSupply = assignedSupply.add(gmtVal);
          return false; 
        }

        stage = Stages.Failed;
        RefundSent(msg.sender, ethVal);  // Log successful refund 

        return true;
    }
}
