SHELL := /bin/bash
.DEFAULT_GOAL := help

INVENTORY      ?= inventory/hosts.yml
SSH_KEY        := $(HOME)/.ssh/id_ed25519
ANSIBLE_PUBKEY := files/ansible_id_ed25519.pub
HOST           ?=
USER           ?=
KEY            ?= $(SSH_KEY)
TAGS           ?=

# Colours
BOLD  := \033[1m
RESET := \033[0m

##@ Setup

.PHONY: setup
setup: _check-uv _install-ansible _install-collections _generate-key _install-hooks ## Set up the control node (install Ansible via uv, collections, SSH key, git hooks)
	@echo -e "$(BOLD)Control node is ready.$(RESET)"
	@echo -e "Next steps:"
	@echo -e "  1. make copy-key HOST=<host> USER=<user>   # copy the ansible SSH key to each target host"
	@echo -e "  2. make bootstrap HOST=<host> USER=<user>  # create the ansible user on the host"
	@echo -e "  3. make apply HOST=<host>                  # apply full configuration"
	@echo -e ""
	@echo -e "  Ansible SSH public key: $(SSH_KEY).pub"

.PHONY: _check-uv
_check-uv:
	@command -v uv > /dev/null 2>&1 || { \
	  echo "uv not found. Install it with:"; \
	  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
	  echo "Then restart your shell and run 'make setup' again."; \
	  exit 1; \
	}

.PHONY: _install-ansible
_install-ansible:
	@if command -v ansible-playbook > /dev/null 2>&1; then \
	  echo "Ansible already installed: $$(ansible --version | head -1)"; \
	else \
	  echo "Installing ansible-core via uv..."; \
	  uv tool install ansible-core; \
	  command -v pyenv > /dev/null 2>&1 && pyenv rehash || true; \
	fi

.PHONY: _install-collections
_install-collections:
	@echo "Installing required Ansible collections..."
	@"$(HOME)/.local/bin/ansible-galaxy" collection install -r requirements.yml --upgrade

.PHONY: _generate-key
_generate-key:
	@if [ -f "$(SSH_KEY)" ]; then \
	  echo "SSH key already exists: $(SSH_KEY)"; \
	else \
	  echo "Generating SSH key pair at $(SSH_KEY) ..."; \
	  ssh-keygen -t ed25519 -C "ansible@fra" -f "$(SSH_KEY)" -N ""; \
	  echo "Key generated. Public key:"; \
	  cat "$(SSH_KEY).pub"; \
	fi

.PHONY: _install-hooks
_install-hooks:
	@command -v pre-commit > /dev/null 2>&1 || { \
	  echo "Installing pre-commit via uv..."; \
	  uv tool install pre-commit; \
	}
	@echo "Installing git pre-commit hooks..."
	@pre-commit install

.PHONY: copy-key
copy-key: ## Copy the ansible SSH public key to a target host  (HOST=<host> USER=<user>)
	@[ -n "$(HOST)" ] || { echo "Usage: make copy-key HOST=<host> USER=<user>"; exit 1; }
	@[ -n "$(USER)" ] || { echo "Usage: make copy-key HOST=<host> USER=<user>"; exit 1; }
	ssh-copy-id -f -i $(ANSIBLE_PUBKEY) "$(USER)@$(HOST)"

##@ Provisioning

.PHONY: bootstrap
bootstrap: ## Bootstrap a new host: create the ansible user  (HOST=<host> USER=<user>)
	@[ -n "$(HOST)" ] || { echo "Usage: make bootstrap HOST=<host> USER=<user>"; exit 1; }
	@[ -n "$(USER)" ] || { echo "Usage: make bootstrap HOST=<host> USER=<user>"; exit 1; }
	ansible-playbook playbooks/bootstrap.yml \
	  -i $(INVENTORY) \
	  -l $(HOST) \
	  --ask-become-pass \
	  --private-key "$(KEY)" \
	  -e "ansible_user=$(USER)"

.PHONY: apply
apply: ## Apply the full configuration to all hosts (or HOST=<host>, TAGS=<tags>)
	ansible-playbook site.yml -i $(INVENTORY) $(if $(HOST),-l $(HOST),) $(if $(TAGS),--tags $(TAGS),)

.PHONY: check
check: ## Dry-run: show what would change without applying anything (HOST=, TAGS= supported)
	ansible-playbook site.yml -i $(INVENTORY) $(if $(HOST),-l $(HOST),) $(if $(TAGS),--tags $(TAGS),) --check --diff

##@ Quality

.PHONY: lint
lint: ## Run all linters (yamllint, ansible-lint, syntax check, inventory validation)
	@echo -e "$(BOLD)Running yamllint...$(RESET)"
	yamllint -c .yamllint.yml .
	@echo -e "\n$(BOLD)Running ansible-lint...$(RESET)"
	ansible-lint
	@echo -e "\n$(BOLD)Running syntax check...$(RESET)"
	ansible-playbook --syntax-check site.yml
	@echo -e "\n$(BOLD)Validating inventory...$(RESET)"
	python3 tests/scripts/validate-inventory.py

##@ Operations

.PHONY: ping
ping: ## Test SSH connectivity to all managed hosts
	ansible all -i $(INVENTORY) -m ping

.PHONY: scan-hosts
scan-hosts: ## Scan and trust SSH fingerprints for any new inventory host
	bash scripts/scan-new-hosts.sh $(INVENTORY)

##@ Help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(BOLD)<target>$(RESET)\n"} \
	  /^[a-zA-Z_-]+:.*?##/ { printf "  $(BOLD)%-18s$(RESET) %s\n", $$1, $$2 } \
	  /^##@/ { printf "\n$(BOLD)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)
