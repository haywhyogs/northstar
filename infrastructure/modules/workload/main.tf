# Everything one workload (app) needs in one environment. Each team calls this module once per environment.
# Teams share the platform (AKS, SQL server, Service Bus namespace) but get their OWN identity, database,
# queues and Key Vault, so one team can never read another team's data or secrets.

locals {
  name            = "${var.app}-${var.environment}"
  namespace       = coalesce(var.namespace, local.name)
  service_account = coalesce(var.service_account, var.app)
  queues          = coalesce(var.queues, [var.app])
  tags            = merge(var.tags, { workload = var.app })
}

data "azurerm_client_config" "current" {}

# ---------- Identity: the app's own Entra ID identity (workload identity) ----------

resource "azurerm_user_assigned_identity" "this" {
  name                = "id-${local.name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = local.tags
}

# Trust rule: "a token from THIS cluster, for THIS service account in THIS namespace, may act as this identity".
# No secret is involved: Kubernetes signs a token, Entra ID checks it against this rule.
resource "azurerm_federated_identity_credential" "this" {
  name                      = "aks-${local.namespace}-${local.service_account}"
  user_assigned_identity_id = azurerm_user_assigned_identity.this.id
  issuer                    = var.oidc_issuer_url
  subject                   = "system:serviceaccount:${local.namespace}:${local.service_account}"
  audience                  = ["api://AzureADTokenExchange"]
}

# ---------- Database: the app's own database on the shared SQL server ----------

# azurerm can't turn on the free offer, so this uses Microsoft's own API directly (azapi).
# Values from https://learn.microsoft.com/azure/azure-sql/database/free-offer
resource "azapi_resource" "database" {
  type      = "Microsoft.Sql/servers/databases@2023-08-01"
  name      = var.app
  parent_id = var.sql_server_id
  location  = var.location
  tags      = local.tags

  body = {
    sku = {
      name     = "GP_S_Gen5" # General Purpose, serverless
      tier     = "GeneralPurpose"
      family   = "Gen5"
      capacity = 2
    }
    properties = {
      createMode                       = "Default"
      maxSizeBytes                     = 34359738368 # 32 GB, the free limit
      requestedBackupStorageRedundancy = "Local"
      useFreeLimit                     = true
      freeLimitExhaustionBehavior      = "AutoPause" # free allowance used up = pause, never bill
    }
  }
}

# ---------- Messaging: the app's own queues ----------

resource "azurerm_servicebus_queue" "this" {
  for_each     = toset(local.queues)
  name         = each.value
  namespace_id = var.servicebus_namespace_id

  lock_duration                        = "PT30S" # a worker has 30 s to finish before the message is redelivered
  max_delivery_count                   = 5       # then it moves to the dead-letter queue
  default_message_ttl                  = "P1D"   # the local emulator allows only 1 hour
  dead_lettering_on_message_expiration = true    # expired messages are kept for redrive, not lost
}

resource "azurerm_role_assignment" "queue_sender" {
  for_each             = azurerm_servicebus_queue.this
  scope                = each.value.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

resource "azurerm_role_assignment" "queue_receiver" {
  for_each             = azurerm_servicebus_queue.this
  scope                = each.value.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# ---------- Secrets: the app's own Key Vault, private endpoint only ----------

resource "azurerm_key_vault" "this" {
  name                       = var.key_vault_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true  # permissions through Azure roles, not vault access policies
  soft_delete_retention_days = 7     # minimum: deleted secrets can be recovered for 7 days
  purge_protection_enabled   = false # dev/staging only, so the environment can be destroyed and rebuilt

  # Private endpoint only, unless an operator IP is set for a setup task (ADR-0010).
  public_network_access_enabled = var.operator_ip != null
  network_acls {
    default_action = "Deny"
    bypass         = "None"
    ip_rules       = var.operator_ip == null ? [] : [var.operator_ip]
  }

  tags = local.tags
}

resource "azurerm_private_endpoint" "key_vault" {
  name                = "pe-${var.key_vault_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-${var.key_vault_name}"
    private_connection_resource_id = azurerm_key_vault.this.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.key_vault_dns_zone_id]
  }
}

# The app may READ secrets.
resource "azurerm_role_assignment" "secrets_user" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# The operator may WRITE secrets (e.g. the JWT signing key). Values never pass through Terraform or Git.
resource "azurerm_role_assignment" "secrets_officer" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.operator_object_id
}
