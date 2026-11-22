# Remote state storage for every Northstar Terraform environment (ADR-0008).
# Created once, before anything else. Everything else stores its state here.

data "azurerm_client_config" "current" {}

locals {
  tags = {
    project     = "northstar"
    environment = "shared"
    owner       = var.owner
    managed_by  = "terraform"
    purpose     = "terraform-state"
  }
}

# Storage account names must be globally unique, 3-24 lowercase letters/digits: add a random suffix.
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "tfstate" {
  name     = "rg-northstar-tfstate"
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "tfstate" {
  name                     = "stnorthstartf${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = azurerm_resource_group.tfstate.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # cheapest; production would use ZRS or GRS
  account_kind             = "StorageV2"

  # Security baseline
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false # no anonymous access, ever
  shared_access_key_enabled       = false # no account keys: only Entra ID identities with an RBAC role
  default_to_oauth_authentication = true  # the Azure Portal also uses Entra ID, not keys
  local_user_enabled              = false # no SFTP/local-user logins
  # Public endpoint stays on so the laptop and GitHub runners can reach it; access is identity-only.

  blob_properties {
    versioning_enabled = true # every write keeps the previous version: the state-recovery drill relies on this

    delete_retention_policy {
      days = var.soft_delete_days # deleted state blobs can be undeleted
    }

    container_delete_retention_policy {
      days = var.soft_delete_days
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.tfstate.id # created through Azure Resource Manager
  container_access_type = "private"
}

# Owning the subscription doesn't allow reading blobs (that's the "data plane"). Grant it explicitly
# to whoever runs this, so `terraform init` in the environments can use Entra ID auth.
# The CI/CD identity gets the same role later (Day 5).
resource "azurerm_role_assignment" "operator_blob_access" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}
