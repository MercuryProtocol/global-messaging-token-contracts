/*
  Abstract contract for the full ERC 20 Token standard
  https://github.com/ethereum/EIPs/issues/20
*/

pragma solidity ^0.4.11;

library SafeMath {
    function mul(uint256 a, uint256 b) internal returns (uint256) {
      uint256 c = a * b;
      assert(a == 0 || c / a == b);
      return c;
    }

    function div(uint256 a, uint256 b) internal returns (uint256) {
      assert(b > 0);
      uint256 c = a / b;
      assert(a == b * c + a % b);
      return c;
    }

    function sub(uint256 a, uint256 b) internal returns (uint256) {
      assert(b <= a);
      return a - b;
    }

    function add(uint256 a, uint256 b) internal returns (uint256) {
      uint256 c = a + b;
      assert(c >= a && c >= b);
      return c;
    }
}

contract Token {

    /* Total amount of tokens */
    uint256 public totalSupply;

    /*
     * Events
     */
    event Transfer(address indexed from, address indexed to, uint value);
    event Approval(address indexed owner, address indexed spender, uint value);

    /*
     * Public functions
     */

    // @notice send `value` token to `to` from `msg.sender`
    // @param to The address of the recipient
    // @param value The amount of token to be transferred
    // @return Whether the transfer was successful or not
    function transfer(address to, uint value) public returns (bool);

    // @notice send `value` token to `to` from `from` on the condition it is approved by `from`
    // @param from The address of the sender
    // @param to The address of the recipient
    // @param value The amount of token to be transferred
    // @return Whether the transfer was successful or not
    function transferFrom(address from, address to, uint value) public returns (bool);

    // @notice `msg.sender` approves `spender` to spend `value` tokens
    // @param spender The address of the account able to transfer the tokens
    // @param value The amount of tokens to be approved for transfer
    // @return Whether the approval was successful or not
    function approve(address spender, uint value) public returns (bool);

    // @param owner The address from which the balance will be retrieved
    // @return The balance
    function balanceOf(address owner) public constant returns (uint);

    // @param owner The address of the account owning tokens
    // @param spender The address of the account able to transfer the tokens
    // @return Amount of remaining tokens allowed to spent
    function allowance(address owner, address spender) public constant returns (uint);
}

contract StandardToken is Token {
    /*
     *  Storage
     */
    mapping (address => uint) balances;
    mapping (address => mapping (address => uint)) allowances;

    /*
     *  Public functions
     */

    function transfer(address to, uint value) public returns (bool) {
        if (balances[msg.sender] < value)
            // Balance too low
            revert();
        balances[msg.sender] -= value;
        balances[to] += value;
        Transfer(msg.sender, to, value);
        return true;
    }

    function transferFrom(address from, address to, uint value) public returns (bool) {
        if (balances[from] < value || allowances[from][msg.sender] < value)
            // Balance or allowance too low
            revert();
        balances[to] += value;
        balances[from] -= value;
        allowances[from][msg.sender] -= value;
        Transfer(from, to, value);
        return true;
    }

    function approve(address spender, uint value) public returns (bool) {
        allowances[msg.sender][spender] = value;
        Approval(msg.sender, spender, value);
        return true;
    }

    function allowance(address owner, address spender) public constant returns (uint) {
        return allowances[owner][spender];
    }

    function balanceOf(address owner) public constant returns (uint) {
        return balances[owner];
    }
}


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
        assert((now > endBlock) || assignedSupply >= minCap);
        _;
    }

    modifier respectTimeFrame() {
        assert((now > startBlock) && (now < endBlock));
        _;
    }

    modifier atStage(Stages _stage) {
        assert(stage == _stage);
        _;
    }

    // TODO: Use a DELEGATECALL to forward data and calls??
    // TODO: Add ownable and pausable contracts: https://github.com/iExecBlockchainComputing/rlc-token/blob/master/contracts/Ownable.sol
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

        ethFundMultiSig.transfer(this.balance);
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
