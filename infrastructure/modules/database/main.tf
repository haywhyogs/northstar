# Azure SQL logical server for the environment. Each workload gets its own database (workload module).
# Entra ID only: there is no SQL admin password at all.

resource "azurerm_mssql_server" "this" {
  name                          = var.name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "12.0"
  minimum_tls_version           = "1.2"
  public_network_access_enabled = false # reachable only through private endpoints

  azuread_administrator {
    login_username              = var.entra_admin_login
    object_id                   = var.entra_admin_object_id
    azuread_authentication_only = true
  }

  tags = var.tags
}
