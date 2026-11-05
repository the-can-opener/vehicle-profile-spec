PYTHON ?= tools/.venv/bin/python
VPROFILE ?= tools/.venv/bin/vprofile
VSS_SOURCE ?= ../vehicle_signal_specification
.PHONY: mandatory_targets test lint types schemas skills generated-check examples catalog build wheel-check clean
mandatory_targets: lint types generated-check test examples wheel-check
lint:
	tools/.venv/bin/ruff check tools/src tests scripts/*.py noxfile.py
	tools/.venv/bin/ruff format --check tools/src tests scripts/*.py noxfile.py
types:
	tools/.venv/bin/mypy --config-file tools/pyproject.toml tools/src
schemas skills:
	$(PYTHON) scripts/generate.py
generated-check:
	$(PYTHON) scripts/generate.py --check
test:
	$(PYTHON) -m pytest -q tests
examples:
	$(PYTHON) scripts/check-examples.py
wheel-check:
	$(PYTHON) scripts/check-build.py
clean:
	python3 scripts/clean.py
catalog:
	VSS_SOURCE="$(VSS_SOURCE)" ./scripts/catalog.sh
build:
	uv build --project tools --wheel
