# Central logs and metrics for the environment: one Log Analytics workspace, plus Application Insights on top of it.

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days
  daily_quota_gb      = var.daily_quota_gb
  # Entra ID only (no shared workspace keys), like Service Bus and the state storage.
  local_authentication_enabled = var.local_authentication_enabled
  tags                         = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "appi-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
  tags                = var.tags
}
