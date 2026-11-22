# Service Bus namespace shared by the environment. Each workload gets its own queues (workload module).

resource "azurerm_servicebus_namespace" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic" # Private endpoints need Premium (ADR-0001)
  local_auth_enabled  = false   # no connection strings / SAS keys: Entra ID identities only
  minimum_tls_version = "1.2"
  tags                = var.tags
}
