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
    string public version = "1.0";

    /*
    *  Multi-sig wallets
    */
    address public ethFundMultiSig;  // Multi-sig address for ETH owned by Radical App LLC
    address public gmtFundMultiSig;  // Multi-sig address for GMT allocated to Radical App LLC development and User Growth Pool

    /*
    *  Crowdsale parameters
    */
    bool public isFinalized;  // Switched to true in operational state
    uint256 public startBlock;
    uint256 public endBlock;
    uint256 public constant gmtFund = 500 * (10**6) * 10**decimals;  // 500M GMT reserved
    uint256 public constant tokenExchangeRate = 4316;  // Units of GMT per ETH
    uint256 public constant tokenCreationCap =  1000 * (10**6) * 10**decimals;
    uint256 public constant tokenCreationMin =  1000 * (10**6) * 10**decimals;
    // TODO: Need to add 30 days period??

    /*
    *  Events
    */
    event RefundSent(address indexed _to, uint256 _value);
    event CreateGMT(address indexed _to, uint256 _value);

    /*
    *  Constructor
    */
    function GMToken(
        address _ethFundMultiSig,
        address _gmtFundMultiSig,
        uint256 _startBlock,
        uint256 _endBlock)
    {
      isFinalized = false;  // Controls pre through crowdsale state
      ethFundMultiSig = _ethFundMultiSig;
      gmtFundMultiSig = _gmtFundMultiSig;
      startBlock = _startBlock;
      endBlock = _endBlock;
      totalSupply = gmtFund; // Start total supply with reserved GMT amount
      balances[gmtFundMultiSig] = gmtFund;  // Deposit Radical App LLC share into Multi-sig
      CreateGMT(gmtFundMultiSig, gmtFund);  // Log Radical App LLC fund  
    }

    // @notice Create `msg.value` ETH worth of GMT
    function createTokens() payable external {
      assert(isFinalized);
      assert(block.number > startBlock);
      assert(block.number <= endBlock);
      assert(msg.value == 0);

      // Check that we're not over totals
      uint256 tokens = msg.value.mul(tokenExchangeRate); 
      uint256 checkedSupply = totalSupply.add(tokens);

      // Return money if reached token cap
      assert(checkedSupply <= tokenCreationCap); 

      totalSupply = checkedSupply;
      balances[msg.sender] += tokens;
      CreateGMT(msg.sender, tokens);  // Logs token creation for UI purposes
    }

    // @notice Ends the funding period and sends the ETH to Multi-sig wallet
    function finalize() external {
      assert(isFinalized);
      assert(msg.sender != gmtFundMultiSig);  // Locks finalize to the ultimate ETH owner
      assert(totalSupply >= tokenCreationMin); // Must sell minimum to transition to operational state
      // Must sell token creation cap amount to transition to operational state
      if (block.number <= endBlock && totalSupply != tokenCreationCap) 
        return false; 

      // Transition to operational
      isFinalized = true;

      if(!gmtFundMultiSig.send(this.balance))
        return false;
    }

    // @notice Allows contributors to recover their ETH in the case of a failed funding campaign
    function refund() external {
      assert(isFinalized);  // Prevents refund if operational
      assert(block.number > endBlock);  // Prevents refund until sale period is over
      assert(totalSupply < tokenCreationMin);  // No refunds if we sold enough
      assert(msg.sender != gmtFundMultiSig);  // Radical App LLC not entitled to a refund

      uint256 gmtVal = balances[msg.sender];
      uint256 ethVal = gmtVal.div(tokenExchangeRate);
      require(gmtVal > 0); // Prevent refund if sender balance is 0

      balances[msg.sender] -= gmtVal;
      totalSupply = totalSupply.sub(gmtVal);
      
      if(!msg.sender.send(ethVal)) {
        balances[msg.sender] += gmtVal;
        totalSupply = totalSupply.add(gmtVal);
        return false; 
      }

      RefundSent(msg.sender, ethVal);  // Log successful refund 
    }
}
