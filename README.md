## To set up virtualenv:

1. `virtualenv -p python3 venv3`
2. `source venv3/bin/activate`
3. `pip3 install -r requirements.txt`

## To run tests:

`python -m unittest tests.tokens.test_gmt_token`


## TODO: 
- Add tests for circuit breaker
- Add tests for BAT Safe
- Add scripts to concatenate all files into one
- Add deployment scripts using pyethereum
