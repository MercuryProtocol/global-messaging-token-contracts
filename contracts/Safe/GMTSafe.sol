pragma solidity 0.4.17;

import 'contracts/Tokens/StandardToken.sol';

// @title GMT Safe contract - Contract to record employee token allocations
// @author Preethi Kasireddy - <preethi@preethireddy.com>

// Need to deposit X number of GMT here
contract GMTSafe {

  /*
    *  GMTSafe parameters
  */
  mapping (address => uint256) allocations;
  uint256 public unlockDate;
  StandardToken public gmtAddress;


  function GMTSafe(StandardToken _gmtAddress) public {
    require(address(_gmtAddress) != 0x0);

    gmtAddress = _gmtAddress;
    unlockDate = now + 6 * 30 days;

    // TODO: Add allocations (must store the token grain amount to be transferred, i.e. 7000 * 10**18)
    allocations[0] = 0;
  }

  /// @notice transfer `allocations[msg.sender]` tokens to `msg.sender` from this contract
  /// @dev The GMT allocations given to the msg.sender are transfered to their account if the lockup period is over
  /// @return boolean indicating whether the transfer was successful or not
  function unlock() external {
    require(now >= unlockDate);

    uint256 entitled = allocations[msg.sender];
    require(entitled > 0);
    allocations[msg.sender] = 0;

    if (!StandardToken(gmtAddress).transfer(msg.sender, entitled)) {
        revert();  // Revert state due to unsuccessful refund
    }
  }
}
