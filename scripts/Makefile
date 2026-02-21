.PHONY: setup test import disable help clean prepare

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Mattermost User Management Toolkit"
	@echo "=================================="
	@echo "Targets:"
	@echo "  setup        : Create virtual environment and install dependencies"
	@echo "  test         : Run automated smoke tests (requires Docker)"
	@echo "  import       : Run the import script (dry-run by default)"
	@echo "  sync         : Run import with team sync (removes users not in CSV from team)"
	@echo "  disable      : Run the disable script"
	@echo "  prepare      : Convert members export CSV to users.csv"
	@echo "  clean        : Remove virtual environment and artifacts"
	@echo ""

setup: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

test: setup
	$(PYTHON) -m pytest test_smoke.py

CSV ?= ../users.csv
DISABLE_CSV ?= ../disable.csv
ARGS ?=

INPUT ?= ../clubcollect.csv
OUTPUT ?= ../users.csv

prepare: setup
	$(PYTHON) prepare.py $(INPUT) --output $(OUTPUT)

import: setup
	$(PYTHON) import_users.py --csv $(CSV) $(ARGS)

sync: setup
	$(PYTHON) import_users.py --csv $(CSV) --sync-team $(ARGS)

disable: setup
	$(PYTHON) disable_users.py --file $(DISABLE_CSV) $(ARGS)

clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf .pytest_cache
