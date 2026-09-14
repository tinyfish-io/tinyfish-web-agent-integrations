.PHONY: format lint test clean

format:
	ruff format src tests
	ruff check --fix src tests

lint:
	ruff check src tests

test:
	pytest tests -v

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
