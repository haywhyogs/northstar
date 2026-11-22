# Network for one environment: a VNet with two subnets, each protected by a network security group (NSG).

resource "azurerm_virtual_network" "this" {
  name                = "vnet-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.address_space]
  tags                = var.tags
}

resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.aks_subnet_prefix]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "snet-private-endpoints"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.private_endpoints_subnet_prefix]
  # Apply NSG rules to private endpoints too (off by default in Azure).
  private_endpoint_network_policies = "Enabled"
}

# AKS subnet: Azure's default rules for now (VNet traffic and load-balancer probes allowed, other inbound denied).
# Ingress rules are added with the AKS cluster.
resource "azurerm_network_security_group" "aks" {
  name                = "nsg-${var.name}-aks"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# Private endpoint subnet: only the AKS subnet may reach the databases (1433) and Key Vault (443).
resource "azurerm_network_security_group" "private_endpoints" {
  name                = "nsg-${var.name}-private-endpoints"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  security_rule {
    name                       = "allow-aks-to-sql-and-keyvault"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = var.aks_subnet_prefix
    source_port_range          = "*"
    destination_address_prefix = var.private_endpoints_subnet_prefix
    destination_port_ranges    = ["1433", "443"]
  }

  security_rule {
    name                       = "deny-all-other-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_address_prefix      = "VirtualNetwork"
    source_port_range          = "*"
    destination_address_prefix = "*"
    destination_port_range     = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}

resource "azurerm_subnet_network_security_group_association" "private_endpoints" {
  subnet_id                 = azurerm_subnet.private_endpoints.id
  network_security_group_id = azurerm_network_security_group.private_endpoints.id
}

# Private DNS zones ("private phone books"). Inside this VNet, a service's normal name
# (e.g. sql-x.database.windows.net) resolves to its private endpoint's IP instead of the public one.
# Zone names are fixed by Microsoft for each service.
locals {
  private_dns_zones = {
    sql       = "privatelink.database.windows.net"
    key_vault = "privatelink.vaultcore.azure.net"
  }
}

resource "azurerm_private_dns_zone" "this" {
  for_each            = local.private_dns_zones
  name                = each.value
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# A zone only answers for VNets linked to it.
resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each              = local.private_dns_zones
  name                  = "link-${var.name}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.this[each.key].name
  virtual_network_id    = azurerm_virtual_network.this.id
  registration_enabled  = false
  tags                  = var.tags
}
