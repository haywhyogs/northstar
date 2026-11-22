# The dev environment: the shared platform foundation that every team's dev namespace uses.
# staging uses the same modules with different settings (only the locals below differ).

locals {
  environment = "dev"
  location    = "canadacentral"
  name        = "northstar-${local.environment}"

  network = {
    address_space                   = "10.20.0.0/16"
    aks_subnet_prefix               = "10.20.0.0/22" # 1,024 addresses for nodes and pods
    private_endpoints_subnet_prefix = "10.20.8.0/24"
  }
  log_daily_quota_gb = 0.5

  tags = {
    project     = "northstar"
    environment = local.environment
    owner       = "platform-team"
    managed_by  = "terraform"
  }
}

data "azurerm_client_config" "current" {}

# Some Azure names must be globally unique: add a short random suffix, kept stable in state.
resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = local.location
  tags     = local.tags
}

module "networking" {
  source = "../../modules/networking"

  name                            = local.name
  resource_group_name             = azurerm_resource_group.this.name
  location                        = local.location
  address_space                   = local.network.address_space
  aks_subnet_prefix               = local.network.aks_subnet_prefix
  private_endpoints_subnet_prefix = local.network.private_endpoints_subnet_prefix
  tags                            = local.tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  name                = local.name
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  daily_quota_gb      = local.log_daily_quota_gb
  tags                = local.tags
}

module "registry" {
  source = "../../modules/registry"

  name                = "acrnorthstar${local.environment}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  tags                = local.tags
}

module "messaging" {
  source = "../../modules/messaging"

  name                = "sb-${local.name}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  tags                = local.tags
}

module "database" {
  source = "../../modules/database"

  name                  = "sql-${local.name}-${random_string.suffix.result}"
  resource_group_name   = azurerm_resource_group.this.name
  location              = local.location
  entra_admin_login     = "northstar-sql-admin"
  entra_admin_object_id = data.azurerm_client_config.current.object_id # production: an Entra ID group
  tags                  = local.tags
}
