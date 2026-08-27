.PHONY: all format lint test clean

all: format lint test

format:
	ruff format tinyfish_hermes tests
	ruff check --fix tinyfish_hermes tests

lint:
	ruff check tinyfish_hermes tests
	mypy tinyfish_hermes

test:
	pytest tests -v

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
