# Container registry shared by all teams in the environment. Images are pushed by CI and pulled by AKS,
# both with Entra ID identities: the admin username/password is disabled.

resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic" # Private endpoints need Premium (ADR-0001)
  admin_enabled       = false
  tags                = var.tags
}
