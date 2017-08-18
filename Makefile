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



