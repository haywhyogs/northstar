terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state. The details come from backend.hcl at `terraform init` time.
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  # Subscription comes from ARM_SUBSCRIPTION_ID, never from code.
  storage_use_azuread             = true
  resource_provider_registrations = "core"
  resource_providers_to_register = [
    "Microsoft.ContainerRegistry",
    "Microsoft.ContainerService",
    "Microsoft.Insights",
    "Microsoft.KeyVault",
    "Microsoft.ManagedIdentity",
    "Microsoft.Network",
    "Microsoft.OperationalInsights",
    "Microsoft.ServiceBus",
    "Microsoft.Sql",
  ]
}
