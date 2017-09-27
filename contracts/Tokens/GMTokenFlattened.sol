pragma solidity 0.4.15;

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

    /// @notice send `value` token to `to` from `msg.sender`
    /// @param to The address of the recipient
    /// @param value The amount of token to be transferred
    /// @return Whether the transfer was successful or not
    function transfer(address to, uint value) public returns (bool);

    /// @notice send `value` token to `to` from `from` on the condition it is approved by `from`
    /// @param from The address of the sender
    /// @param to The address of the recipient
    /// @param value The amount of token to be transferred
    /// @return Whether the transfer was successful or not
    function transferFrom(address from, address to, uint value) public returns (bool);

    /// @notice `msg.sender` approves `spender` to spend `value` tokens
    /// @param spender The address of the account able to transfer the tokens
    /// @param value The amount of tokens to be approved for transfer
    /// @return Whether the approval was successful or not
    function approve(address spender, uint value) public returns (bool);

    /// @param owner The address from which the balance will be retrieved
    /// @return The balance
    function balanceOf(address owner) public constant returns (uint);

    /// @param owner The address of the account owning tokens
    /// @param spender The address of the account able to transfer the tokens
    /// @return Amount of remaining tokens allowed to spent
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
        // Do not allow transfer to 0x0 or the token contract itself
        require((to != 0x0) && (to != address(this)));
        if (balances[msg.sender] < value)
            revert();  // Balance too low
        balances[msg.sender] -= value;
        balances[to] += value;
        Transfer(msg.sender, to, value);
        return true;
    }

    function transferFrom(address from, address to, uint value) public returns (bool) {
        if (balances[from] < value || allowances[from][msg.sender] < value)
            revert(); // Balance or allowance too low
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

library SafeMath {
    function mul(uint256 a, uint256 b) internal constant returns (uint256) {
      uint256 c = a * b;
      assert(a == 0 || c / a == b);
      return c;
    }

    function div(uint256 a, uint256 b) internal constant returns (uint256) {
      assert(b > 0);
      uint256 c = a / b;
      assert(a == b * c + a % b);
      return c;
    }

    function sub(uint256 a, uint256 b) internal constant returns (uint256) {
      assert(b <= a);
      return a - b;
    }

    function add(uint256 a, uint256 b) internal constant returns (uint256) {
      uint256 c = a + b;
      assert(c >= a && c >= b);
      return c;
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
        assert(msg.value > 0);

        // Check that we're not over totals
        uint256 tokens = msg.value.mul(tokenExchangeRate); 
        uint256 checkedSupply = assignedSupply.add(tokens);

        // Return money if we're over total token supply
        assert(checkedSupply <= totalSupply); 

        balances[msg.sender] += tokens;
        assignedSupply = checkedSupply;
        ClaimGMT(msg.sender, tokens);  // Logs token creation for UI purposes
    }


    /// @notice Updates registration status of an address for sale participation
    /// @param target Address that will be registered or deregistered
    /// @param isRegistered New registration status of address
    function changeRegistrationStatus(address target, bool isRegistered)
        public
        onlyBy(owner) 
    {
        registered[target] = isRegistered;
    }

    /// @notice Updates registration status for multiple addresses for participation
    /// @param targets Addresses that will be registered or deregistered
    /// @param isRegistered New registration status of addresses
    function changeRegistrationStatuses(address[] targets, bool isRegistered)
        public
        onlyBy(owner) 
    {
        for (uint i = 0; i < targets.length; i++) {
            changeRegistrationStatus(targets[i], isRegistered);
        }
    }


    /// @notice Tells whether user is registered for participation
    /// @param target Addresses to check registration list against
    /// @return bool True if user is registered, false otherwise
    function isAddressRegistered(address target) external returns (bool) {
        return registered[target];
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
        assert(assignedSupply - gmtFund < minCap);  // No refunds if we reached min cap
        assert(msg.sender != gmtFundAddress);  // Radical App International not entitled to a refund

        uint256 gmtVal = balances[msg.sender];
        assert(gmtVal > 0); // Prevent refund if sender GMT balance is 0

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

