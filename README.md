## To set up virtualenv:

1. `virtualenv -p python3 venv3`
2. `source venv3/bin/activate`
3. `pip3 install -r requirements.txt`

NOTE: You'll need to have Python3 and Solidity installed. For Solidity, see http://solidity.readthedocs.io/en/develop/installing-solidity.html

## To run tests:

`make test`

## To deploy:

`make deploy-contracts`

NOTE: Please ensure to update the file `scripts/tokenSaleConfig.json` with the appropriate constructor params.

## To create abis:

`make abi-token`

`make abi-safe`

## Directory structure
```
| abi
|   -- GMToken.json (ABI for GMToken contract)
|   -- GMTSafe.json (ABI for GMTSafe contract)
|
| contracts
|   |-- Safe
|   |   -- GMTSafe.sol (Smart contract for GMTSafe that secure employee allocations during lockup period)
|   |   -- GMTSafeFlattened.sol (Flattened contract for GMTSafe)
|   |
|   |-- Tokens
|   |   -- AbstractToken.sol (Abstract contract for the full ERC 20 Token standard)
|   |   -- GMToken.sol (Main token sale contract)
|   |   -- GMTokenFlattened.sol (Flatteneded contract for GMToken)
|   |   -- StandardToken.sol (Implements ERC 20 Token standard)
|   |
|   |-- Utils
|   |   -- SafeMath.sol (SafeMath library for math operations with safety checks)
|   |   -- GMToken.sol (Main token sale contract)
|   |
|   |-- Wallets
|   |   -- MultiSigWallet.sol (Multisignature wallet implementation)
|   |   -- MultiSigWalletWithDailyLimit.sol (Multisignature wallet with daily limi)
|
| scripts
|   -- deployed_abis.json (ABI for deployed contract)
|   -- eth_abi_creator.py (Scripts for generating abis for smart contracts)
|   -- eth_deploy.py (Scripts for deploying smart contracts)
|   -- eth_transaction_scripts.py (Scripts for handling transactions on deployed contracts)
|   -- tokenSaleConfig.json (Sets contructor params for contracts being deployed using eth_deploy.py)
|
| tests
|   |-- safe
|   |   -- test_gmt_safe.py (Unit tests for GMTSafe contract)
|   |
|   |-- tokens
|   |   -- test_gmt_token.py (Unit tests for GMToken contract)
|   |
|   -- abstract_test.py (Scripts for setting up test environment using pyethereum Tester module)
|
| --.gitignore
| -- Makefile
| -- README.md
| -- requirements.txt
```

## Errors you may run into:
1. Installing Ethereum using pip, which installs scrypt, gives the following error (on MAC):
    ```fatal error: 'openssl/opensslv.h' file not found
    #include <openssl/opensslv.h>
             ^
    1 error generated.
    error: command 'clang' failed with exit status 1```

    - Since OSX version10.11 (El Capitan) or higher no longer includes OpenSSL headers, you will start to have compilation issues of dependencies that require OpenSSL headers.
    - With brew you can install a newer version of openssl and also the headers, but pip is still not able to find it. 
    - To solve this issue we need to use brew to specify the path where the headers are:
    `brew install openssl`
    `env LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix openssl)/include" ppip3 install -r requirements.txt`
