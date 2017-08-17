pragma solidity 0.4.15;

import './../Tokens/StandardToken.sol';

// Need to deposit X number of GMT here
contract GMTSafe {

  /*
    *  GMTSafe parameters
  */
  mapping (address => uint256) allocations;
  uint256 public unlockDate;
  address public gmtAddress;
  uint256 public constant decimals = 18;


  function GMTSafe(address _gmtAddress) {
    require(_gmtAddress != 0x0);

    gmtAddress = _gmtAddress;
    unlockDate = now + 6 * 30 days;

    // TODO: Add allocations
    allocations[0] = 0;
  }

  function unlock() external {
    assert(now >= unlockDate);

    uint256 entitled = allocations[msg.sender];
    allocations[msg.sender] = 0;

    StandardToken(gmtAddress).transfer(msg.sender, entitled * 10**decimals);
  }
}
