.PHONY: update
update:
	uv sync
	uv run pre-commit autoupdate
