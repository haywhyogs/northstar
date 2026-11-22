terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    # Microsoft's provider for Azure options azurerm doesn't support yet (the SQL free offer).
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }
}
