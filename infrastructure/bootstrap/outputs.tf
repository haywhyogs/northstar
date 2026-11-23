output "resource_group_name" {
  value = azurerm_resource_group.tfstate.name
}

output "storage_account_name" {
  value = azurerm_storage_account.tfstate.name
}

output "container_name" {
  value = azurerm_storage_container.tfstate.name
}

output "backend_config_example" {
  description = "Paste into an environment's backend.hcl (git-ignored values are not needed: none of these are secrets)."
  value       = <<-EOT
    resource_group_name  = "${azurerm_resource_group.tfstate.name}"
    storage_account_name = "${azurerm_storage_account.tfstate.name}"
    container_name       = "${azurerm_storage_container.tfstate.name}"
    use_azuread_auth     = true
  EOT
}

# Not secrets: IDs only. Stored as GitHub repository variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID).
output "github_client_id" {
  value = azurerm_user_assigned_identity.github.client_id
}

output "tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}
