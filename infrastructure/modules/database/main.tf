# Azure SQL logical server for the environment. Each workload gets its own database (workload module).
# Entra ID only: there is no SQL admin password at all.

resource "azurerm_mssql_server" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  version             = "12.0"
  minimum_tls_version = "1.2"
  # Private endpoint only, unless an operator IP is set for a setup task (ADR-0010).
  public_network_access_enabled = var.operator_ip != null

  azuread_administrator {
    login_username              = var.entra_admin_login
    object_id                   = var.entra_admin_object_id
    azuread_authentication_only = true
  }

  tags = var.tags
}

# Opens the public endpoint to ONE address only, while operator_ip is set.
resource "azurerm_mssql_firewall_rule" "operator" {
  count            = var.operator_ip == null ? 0 : 1
  name             = "operator"
  server_id        = azurerm_mssql_server.this.id
  start_ip_address = var.operator_ip
  end_ip_address   = var.operator_ip
}

# The private door: a network card in our private endpoint subnet that leads to this server.
resource "azurerm_private_endpoint" "this" {
  count               = var.private_endpoint == null ? 0 : 1
  name                = "pe-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.name}"
    private_connection_resource_id = azurerm_mssql_server.this.id
    subresource_names              = ["sqlServer"]
    is_manual_connection           = false
  }

  # Writes the server's private IP into the private DNS zone automatically.
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_endpoint.dns_zone_id]
  }
}
