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

output "payments_identity_client_id" {
  value = module.payments.identity_client_id
}

output "payments_key_vault_name" {
  value = module.payments.key_vault_name
}

output "payments_database_grant_sql" {
  value = module.payments.database_grant_sql
}
