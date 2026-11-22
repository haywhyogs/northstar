output "identity_client_id" {
  description = "Goes on the Kubernetes service account (azure.workload.identity/client-id annotation)."
  value       = azurerm_user_assigned_identity.this.client_id
}

output "identity_name" {
  description = "The database user name to create (CREATE USER ... FROM EXTERNAL PROVIDER)."
  value       = azurerm_user_assigned_identity.this.name
}

output "namespace" {
  value = local.namespace
}

output "service_account" {
  value = local.service_account
}

output "database_name" {
  value = azapi_resource.database.name
}

output "queue_names" {
  value = [for queue in azurerm_servicebus_queue.this : queue.name]
}

output "key_vault_name" {
  value = azurerm_key_vault.this.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.this.vault_uri
}

# The SQL an operator runs once, connected to this database as the Entra ID admin.
output "database_grant_sql" {
  value = <<-SQL
    CREATE USER [${azurerm_user_assigned_identity.this.name}] FROM EXTERNAL PROVIDER;
    ALTER ROLE db_datareader ADD MEMBER [${azurerm_user_assigned_identity.this.name}];
    ALTER ROLE db_datawriter ADD MEMBER [${azurerm_user_assigned_identity.this.name}];
    ALTER ROLE db_ddladmin ADD MEMBER [${azurerm_user_assigned_identity.this.name}];
  SQL
}
