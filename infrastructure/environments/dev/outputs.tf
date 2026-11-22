output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "vnet_name" {
  value = module.networking.vnet_name
}

output "acr_login_server" {
  value = module.registry.login_server
}

output "servicebus_namespace" {
  value = module.messaging.name
}

output "sql_server_fqdn" {
  value = module.database.fqdn
}

output "aks_name" {
  value = module.aks.name
}

output "aks_oidc_issuer_url" {
  value = module.aks.oidc_issuer_url
}
