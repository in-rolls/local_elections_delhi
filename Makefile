PYTHON ?= python3

.PHONY: fetch build persistence test
fetch:
	$(PYTHON) scripts/fetch_sources.py
	$(PYTHON) scripts/fetch_archives.py

build:
	$(PYTHON) scripts/parse_sources.py
	$(PYTHON) scripts/parse_winners.py
	$(PYTHON) scripts/build_release.py
	$(PYTHON) scripts/parse_cycles.py --root .
	$(PYTHON) scripts/build_cycles.py
	$(PYTHON) scripts/build_persistence.py

persistence:
	$(PYTHON) scripts/build_persistence.py

test:
	$(PYTHON) -m ruff check scripts tests
	$(PYTHON) -m ruff format --check scripts tests
	$(PYTHON) -m pytest -q
