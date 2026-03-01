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

.PHONY: clean
clean:
	@rm -rf .venv
	@rm -rf build dist *.egg-info
	@rm -rf logs
	@find loom -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find loom -type f -name "*.pyc" -delete
	@find loom -type f -name "*.pyo" -delete
	@find loom -type f -name "*.so" -delete
	@find loom -type f -name "*.c" -delete
	@rm -rf .pytest_cache .coverage

.PHONY: compile
compile: install
	@rm -rf build dist *.egg-info
	@uv run --no-dev python scripts/cythonizer.py
