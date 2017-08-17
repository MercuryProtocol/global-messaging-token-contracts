pragma solidity 0.4.15;

import './../Tokens/StandardToken.sol';

// Need to deposit X number of GMT here
contract GMTSafe {

  /*
    *  Contract owner (Radical App International team)
  */
  address public owner;

  /*
    *  GMTSafe parameters
  */
  mapping (address => uint256) allocations;
  uint256 public unlockDate;
  address public GMTAddress;
  uint256 public constant decimals = 18;

  modifier onlyBy(address _account){
      require(msg.sender == _account);  
      _;
  }

  function changeOwner(address _newOwner) onlyBy(owner) {
      owner = _newOwner;
  }

  function GMTSafe(address _GMTAddress) {
    require(_GMTAddress != 0x0);

    owner = msg.sender; // Creator of contract is owner
    GMTAddress = _GMTAddress;
    unlockDate = now + 6 * 30 days;

    // TODO: Add allocations
    allocations[0] = 0;
  }

  function unlock() onlyBy(owner) external {
    assert(now >= unlockDate);

    uint256 entitled = allocations[msg.sender];
    allocations[msg.sender] = 0;

    StandardToken(GMTAddress).transfer(msg.sender, entitled * 10**decimals);
  }
}
