.PHONY: all format lint test integration_test check_imports clean

all: format lint test

TEST_FILE ?= tests/unit_tests/
integration_test: TEST_FILE = tests/integration_tests/

format:
	ruff format langchain_tinyfish tests
	ruff check --fix langchain_tinyfish tests

lint:
	ruff check langchain_tinyfish tests
	mypy langchain_tinyfish

test integration_test:
	pytest $(TEST_FILE) -v

check_imports: $(shell find langchain_tinyfish -name '*.py')
	python scripts/check_imports.py $^

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
