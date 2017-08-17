.PHONY: clean

clean:
	find . -name \*.pyc -o -name \*.pyo -o -name __pycache__ -exec rm -rf {} +