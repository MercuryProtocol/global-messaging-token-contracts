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
- Add transaction processing scripts
- Update to ERC223 standard?
- Add README for audits