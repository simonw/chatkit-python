.PHONY: sync format format-check lint mypy pyright tests gen-docs build-docs serve-docs deploy-docs check

install:
	uv sync --all-extras --all-packages --group dev

format:
	uv run ruff format
	uv run ruff check --fix

format-check:
	uv run ruff format --check

lint:
	uv run ruff check

mypy:
	uv run mypy .

pyright:
	uv run pyright

test:
	PYTHONPATH=. uv run pytest

build:
	uv build

serve-docs:
	uv run mkdocs serve

deploy-docs:
	uv run mkdocs gh-deploy --force --verbose

check: format-check lint pyright test