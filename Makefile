.PHONY: install test lint format precommit

install:
	pip install -e ".[dev,test,docs]"

test:
	pytest

lint:
	flake8 .
	mypy .

format:
	black .
	isort .

precommit:
	pre-commit run --all-files
