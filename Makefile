install:
	uv sync
	uv run pre-commit install -f

update: install
	uv lock --upgrade
	uv sync --all-groups
	uv run pre-commit autoupdate

checks: install
	uv run pre-commit run --all-files

tests: install
	uv run pytest --cov=loom --cov-report=term-missing

lint:
	skip=pytest uv run pre-commit run

prune:
	git fetch -p && for branch in $$(git branch -vv | grep ': gone]' | awk '{print $$1}'); do git branch -D $$branch; done

compile:
	@rm -rf build dist *.egg-info
	@uv run --no-dev python cythonize_package.py

container:
	docker buildx build -t loom:latest .
	docker image prune -f
