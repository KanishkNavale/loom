.PHONY: install
install:
	uv sync
	autohooks activate --force


.PHONY: update
update: install
	uv sync --upgrade
	uv run pre-commit autoupdate

.PHONY: pre-commit
pre-commit: install
	pre-commit run --all-files

.PHONY: tests
tests: install
	uv run pytest
