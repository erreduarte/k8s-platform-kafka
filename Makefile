PYTHON ?= python

ifeq ($(OS),Windows_NT)
WSL_REPO := $(shell wsl wslpath '$(CURDIR)')
ANSIBLE_PIP_SETUP := @echo "Using WSL Ansible toolchain on Windows"
ANSIBLE_COLLECTIONS_SETUP := wsl bash -lc "cd '$(WSL_REPO)/ansible' && ansible-galaxy collection install -r requirements.yml"
ANSIBLE_SYNTAX_CHECK := wsl bash -lc "cd '$(WSL_REPO)' && ansible-playbook --syntax-check ansible/site.yml -i ansible/inventory/hosts.yml"
else
ANSIBLE_PIP_SETUP := $(PYTHON) -m pip install ansible-core
ANSIBLE_COLLECTIONS_SETUP := ansible-galaxy collection install -r ansible/requirements.yml
ANSIBLE_SYNTAX_CHECK := ansible-playbook --syntax-check ansible/site.yml -i ansible/inventory/hosts.yml
endif

.DEFAULT_GOAL := check

.PHONY: setup compile unit-tests argocd-validate check lint drift complexity format \
	validate-commit-msg agent-validate terraform-compile terraform-lint terraform-format \
	gitops-compile gitops-lint gitops-format kafka-compile kafka-lint kafka-format \
	ansible-compile terraform-check gitops-check kafka-check ansible-check

setup:
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -r gitops/requirements-dev.txt
	$(ANSIBLE_PIP_SETUP)
	$(ANSIBLE_COLLECTIONS_SETUP)
	cd kafka && uv sync --locked --all-groups
	$(PYTHON) -m pre_commit install --hook-type commit-msg

terraform-compile:
	terraform -chdir=terraform init -backend=false
	terraform -chdir=terraform validate

gitops-compile:
	$(MAKE) -C gitops compile

kafka-compile:
	$(MAKE) -C kafka compile

ansible-compile:
	$(ANSIBLE_SYNTAX_CHECK)

compile: terraform-compile gitops-compile kafka-compile ansible-compile

unit-tests:
	$(MAKE) -C gitops unit-tests

argocd-validate:
	$(MAKE) -C gitops argocd-validate

check: compile unit-tests
	@echo "monorepo validation passed"

terraform-lint:
	terraform -chdir=terraform fmt -check -recursive

gitops-lint:
	$(MAKE) -C gitops lint

kafka-lint:
	$(MAKE) -C kafka lint

lint: terraform-lint gitops-lint kafka-lint

drift:
	$(MAKE) -C kafka drift

complexity:
	$(MAKE) -C kafka complexity

terraform-format:
	terraform -chdir=terraform fmt -recursive

gitops-format:
	$(MAKE) -C gitops format

kafka-format:
	$(MAKE) -C kafka format

format: terraform-format gitops-format kafka-format

validate-commit-msg:
ifndef MSG
	$(error MSG is required. Usage: make validate-commit-msg MSG="feat(platform): add root harness")
endif
	$(PYTHON) scripts/validate_commit_msg.py "$(MSG)"

agent-validate: validate-commit-msg compile
	@echo agent validation passed - safe to commit

terraform-check: terraform-compile

gitops-check:
	$(MAKE) -C gitops check

kafka-check:
	$(MAKE) -C kafka check

ansible-check: ansible-compile
