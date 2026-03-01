.PHONY: install
install:
	uv sync
	uv run pre-commit install -f


.PHONY: update
update: install
	uv sync --upgrade
	uv run pre-commit autoupdate

.PHONY: checks
checks: install
	uv run pre-commit run --all-files

.PHONY: tests
tests: install
	uv run pytest --cov=loom --cov-report=term-missing
