terraform {
  backend "s3" {
    bucket = "example-terraform-state"
    key    = "example-infrastructure/terraform.tfstate"
    region = "auto"

    # Cloudflare R2 implements the S3 object operations required by Terraform's
    # native lockfile mechanism.
    use_lockfile   = true
    use_path_style = true

    # R2 does not expose AWS IAM, STS, or EC2 metadata APIs.
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
  }
}