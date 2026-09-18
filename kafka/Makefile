.PHONY: setup compile lint check format drift complexity validate-commit-msg agent-validate

ifeq ($(OS),Windows_NT)
VENV_PYTHON := .venv/Scripts/python.exe
else
VENV_PYTHON := .venv/bin/python
endif

PYTHON ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python)

setup:
	uv sync --locked --all-groups
	uv run pre-commit install --hook-type commit-msg

compile:
	$(PYTHON) scripts/compile.py

lint:
	$(PYTHON) -m ruff check . --exclude .venv

check: compile
	@echo check passed

format:
	$(PYTHON) -m ruff format . --exclude .venv

drift:
	$(PYTHON) scripts/check_drift.py

complexity:
	$(PYTHON) scripts/check_complexity.py

validate-commit-msg:
ifndef MSG
	$(error MSG is required. Usage: make validate-commit-msg MSG="feat: add topic helper")
endif
	$(PYTHON) scripts/validate_commit_msg.py "$(MSG)"

agent-validate: validate-commit-msg compile
	@echo agent validation passed - safe to commit
