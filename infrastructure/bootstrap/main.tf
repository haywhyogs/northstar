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

# ---------- CI/CD identity (ADR-0011) ----------
# The identity GitHub Actions signs in as. It lives here, next to the state, because the bootstrap is never
# destroyed: the GitHub setup survives every dev rebuild. Its permissions on dev resources are granted by
# the dev environment itself (recreated with dev).
resource "azurerm_user_assigned_identity" "github" {
  name                = "id-northstar-github"
  resource_group_name = azurerm_resource_group.tfstate.name
  location            = azurerm_resource_group.tfstate.location
  tags                = merge(local.tags, { purpose = "ci-cd" })
}

# OIDC trust rules: "a token from GitHub, for THIS repository, in THIS context, may act as this identity".
# No client secret exists. Each rule matches exactly one context:
#   main    = the build job on the main branch (pushes images)
#   dev     = jobs in the GitHub environment "dev" (deploys to payments-dev)
#   staging = jobs in the GitHub environment "staging", which needs the reviewer's approval first
locals {
  github_subjects = {
    main    = "${var.github_oidc_subject_prefix}:ref:refs/heads/main"
    dev     = "${var.github_oidc_subject_prefix}:environment:dev"
    staging = "${var.github_oidc_subject_prefix}:environment:staging"
  }
}

resource "azurerm_federated_identity_credential" "github" {
  for_each                  = local.github_subjects
  name                      = "github-${each.key}"
  user_assigned_identity_id = azurerm_user_assigned_identity.github.id
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = each.value
  audience                  = ["api://AzureADTokenExchange"]
}

# The pipeline reads Terraform outputs (Azure names) but never writes state: read-only on the state blobs.
resource "azurerm_role_assignment" "github_state_reader" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}
