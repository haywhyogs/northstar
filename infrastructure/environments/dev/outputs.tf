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

# Every workload slice, keyed by Kubernetes namespace. The setup and deploy scripts (and the pipeline) read this.
output "workloads" {
  value = {
    for namespace, workload in {
      "payments-dev"     = module.payments
      "payments-staging" = module.payments_staging
      } : namespace => {
      identity_client_id = workload.identity_client_id
      identity_name      = workload.identity_name
      database_name      = workload.database_name
      queue              = workload.queue_names[0]
      key_vault_name     = workload.key_vault_name
      database_grant_sql = workload.database_grant_sql
    }
  }
}
