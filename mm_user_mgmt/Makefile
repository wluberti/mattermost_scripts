.PHONY: setup test import disable help clean

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
	@echo "  disable      : Run the disable script"
	@echo "  clean        : Remove virtual environment and artifacts"
	@echo ""

setup: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

test: setup
	$(PYTHON) -m pytest test_smoke.py

import: setup
	$(PYTHON) import_users.py --help

disable: setup
	$(PYTHON) disable_users.py --help

clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf .pytest_cache
