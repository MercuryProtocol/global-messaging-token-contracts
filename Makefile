all: init activate clean test
.PHONY: all

init:
	virtualenv -p python3 venv3
	source venv3/bin/activate
	pip3 install -r requirements.txt

activate:
	source venv3/bin/activate

clean:
	find . -name \*.pyc -o -name \*.pyo -o -name __pycache__ -exec rm -rf {} +

test:
	python -m unittest tests.tokens.test_gmt_token
	python -m unittest tests.safe.test_gmt_safe

flatten-token:
	solidity_flattener --solc-paths=contracts=${CURDIR}/contracts/ --output contracts/Tokens/GMTokenFlattened.sol contracts/Tokens/GMToken.sol

flatten-safe:
	solidity_flattener --solc-paths=contracts=${CURDIR}/contracts/ --output contracts/Safe/GMTSafeFlattened.sol contracts/Safe/GMTSafe.sol

abi-token:
	python scripts/eth_abi_creator.py --f contracts/Tokens/GMToken.sol

abi-safe:
	python scripts/eth_abi_creator.py --f contracts/Safe/GMTSafe.sol

deploy-contracts:
	python scripts/eth_deploy.py --f scripts/tokenSaleConfig.json
