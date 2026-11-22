terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0" # any 4.x, never a surprise major upgrade; exact version recorded in .terraform.lock.hcl
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # No backend block on purpose: this config CREATES the remote backend, so its own (tiny) state is local.
  # terraform.tfstate stays on the operator's machine and is git-ignored. See README.md.
}

provider "azurerm" {
  features {}
  # Subscription comes from the ARM_SUBSCRIPTION_ID environment variable, never from code.
  storage_use_azuread             = true   # talk to storage with Entra ID, not account keys (keys are disabled below)
  resource_provider_registrations = "core" # register only the common Azure resource providers
}
