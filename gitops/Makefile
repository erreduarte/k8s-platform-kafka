PYTHON ?= python

.PHONY: setup compile argocd-validate unit-tests lint check format agent-validate validate-commit-msg

setup:
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pre_commit install --hook-type commit-msg

compile:
	$(PYTHON) scripts/validate_repo.py compile

argocd-validate:
	$(PYTHON) scripts/validate_repo.py argocd-validate

unit-tests:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

lint:
	$(PYTHON) -m yamllint -c .yamllint.yml .

check: compile unit-tests

format:
	$(PYTHON) -m yamlfix .

agent-validate: validate-commit-msg compile
	@echo Agent validation passed - safe to commit

validate-commit-msg:
ifndef MSG
	$(error MSG is required. Usage: make validate-commit-msg MSG="feat: add application")
endif
	$(PYTHON) scripts/validate_repo.py validate-commit-msg --msg "$(MSG)"
