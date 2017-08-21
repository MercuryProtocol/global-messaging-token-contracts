## To set up virtualenv:

1. `virtualenv -p python3 venv3`
2. `source venv3/bin/activate`
3. `pip3 install -r requirements.txt`

## To run tests:

`python -m unittest tests.tokens.test_gmt_token`

NOTE: You'll need to have Solidity installed for tests to run. See http://solidity.readthedocs.io/en/develop/installing-solidity.html

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



## TODO: 
- Add tests for BAT Safe (in progress)
- Add scripts to concatenate all files into one
    - https://github.com/BlockCatIO/solidity-flattener
- Add deployment scripts using pyethereum
    - https://www.npmjs.com/package/solc
- Update to ERC223 standard?

"0x4f101b2537eca0148e6973258aefabadd79f66af", "0x31f7ab57673a4523827fae9102962b4c40661171", 754954, 755300

address TEST2: 0xa27360bdb33fb5f857b6e2959077b40633ef0351
address TEST2-b: 0xe156A6Ca661f64Ff4f65C343ec8675dC08E6Ed76
