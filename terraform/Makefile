.DEFAULT_GOAL := check

.PHONY: setup compile lint format check validate-commit-msg agent-validate state-backend-check

setup: ## Initialize the Cloudflare R2 remote state backend
	terraform init -reconfigure

state-backend-check: ## Verify that the initialized backend can read its remote state
	@terraform state pull >/dev/null
	@echo "Remote state is readable"

compile: ## Validate Terraform configuration
	terraform validate

lint: ## Check Terraform formatting without modifying files
	terraform fmt -check -recursive

format: ## Format Terraform configuration files
	terraform fmt -recursive

check: compile ## Run the required local validation gate

validate-commit-msg: ## Validate Conventional Commit format; pass MSG="type: subject"
ifndef MSG
	$(error MSG is required. Usage: make validate-commit-msg MSG="feat: add module")
endif
	@powershell.exe -NoProfile -Command "$${message} = '$(MSG)'; if ($${message} -notmatch '^(feat|fix|docs|chore|refactor|test|ci|perf|style)(\([^)]+\))?!?: .+') { Write-Error 'ERROR: commit message must follow Conventional Commits format'; exit 1 }; Write-Host 'Commit message valid'"

agent-validate: validate-commit-msg compile ## Agent pre-commit gate: validate message, then Terraform
	@echo Agent validation passed - safe to commit