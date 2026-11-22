# The dev environment: the shared platform foundation that every team's dev namespace uses.
# staging uses the same modules with different settings (only the locals below differ).
#
# Modules are pinned to released Git tags (ADR-0009). To roll out a module change: release a new tag,
# bump it here in dev first, then in staging once dev is proven.

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
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/networking?ref=modules/networking/v1.1.0"

  name                            = local.name
  resource_group_name             = azurerm_resource_group.this.name
  location                        = local.location
  address_space                   = local.network.address_space
  aks_subnet_prefix               = local.network.aks_subnet_prefix
  private_endpoints_subnet_prefix = local.network.private_endpoints_subnet_prefix
  tags                            = local.tags
}

module "monitoring" {
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/monitoring?ref=modules/monitoring/v1.1.0"

  name                = local.name
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  daily_quota_gb      = local.log_daily_quota_gb
  tags                = local.tags
}

module "registry" {
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/registry?ref=modules/registry/v1.0.0"

  name                = "acrnorthstar${local.environment}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  tags                = local.tags
}

module "messaging" {
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/messaging?ref=modules/messaging/v1.0.0"

  name                = "sb-${local.name}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  tags                = local.tags
}

module "database" {
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/database?ref=modules/database/v1.1.0"

  name                  = "sql-${local.name}-${random_string.suffix.result}"
  resource_group_name   = azurerm_resource_group.this.name
  location              = local.location
  entra_admin_login     = "northstar-sql-admin"
  entra_admin_object_id = data.azurerm_client_config.current.object_id # production: an Entra ID group
  operator_ip           = var.operator_ip
  private_endpoint = {
    subnet_id   = module.networking.private_endpoints_subnet_id
    dns_zone_id = module.networking.private_dns_zone_ids["sql"]
  }
  tags = local.tags
}

module "aks" {
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/aks?ref=modules/aks/v1.0.0"

  name                = local.name
  resource_group_name = azurerm_resource_group.this.name
  location            = local.location
  subnet_id           = module.networking.aks_subnet_id
  acr_id              = module.registry.id
  vm_size             = "Standard_D2as_v7"                             # B2ms isn't allowed for AKS in this subscription in canadacentral
  admin_object_ids    = [data.azurerm_client_config.current.object_id] # production: an Entra ID group
  tags                = local.tags
}

# The payments team's slice of the platform (ADR-0010). A new team = one more block like this.
module "payments" {
  source = "git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/workload?ref=modules/workload/v1.0.0"

  app                        = "payments"
  environment                = local.environment
  resource_group_name        = azurerm_resource_group.this.name
  location                   = local.location
  oidc_issuer_url            = module.aks.oidc_issuer_url
  sql_server_id              = module.database.id
  servicebus_namespace_id    = module.messaging.id
  key_vault_name             = "kv-payments-dev-${random_string.suffix.result}"
  private_endpoint_subnet_id = module.networking.private_endpoints_subnet_id
  key_vault_dns_zone_id      = module.networking.private_dns_zone_ids["key_vault"]
  operator_object_id         = data.azurerm_client_config.current.object_id
  operator_ip                = var.operator_ip
  tags                       = local.tags
}
