# Credentials are supplied only through the trusted runner environment:
# PROXMOX_VE_ENDPOINT, PROXMOX_VE_API_TOKEN, and PROXMOX_VE_INSECURE.
# Do not add credentials, API tokens, or private keys to Terraform files or tfvars.
provider "proxmox" {}