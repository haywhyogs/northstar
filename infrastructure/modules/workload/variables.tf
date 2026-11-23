variable "app" {
  description = "Workload name, e.g. payments or fx-rates."
  type        = string
}

variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "namespace" {
  description = "Kubernetes namespace. null = <app>-<environment>."
  type        = string
  default     = null
}

variable "service_account" {
  description = "Kubernetes service account the pods run as. null = <app>."
  type        = string
  default     = null
}

variable "oidc_issuer_url" {
  description = "The AKS cluster's OIDC issuer URL (aks module output)."
  type        = string
}

variable "sql_server_id" {
  type = string
}

variable "servicebus_namespace_id" {
  type = string
}

variable "database_name" {
  description = "Database name on the shared SQL server. null = the app name. Set it when two environments share one server."
  type        = string
  default     = null
}

variable "queues" {
  description = "Service Bus queues this workload owns. null = one queue named after the app."
  type        = list(string)
  default     = null
}

variable "key_vault_name" {
  description = "Globally unique, 3-24 letters, digits and hyphens."
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.key_vault_name))
    error_message = "Key Vault names are 3-24 characters: letters, digits and hyphens, starting with a letter."
  }
}

variable "private_endpoint_subnet_id" {
  type = string
}

variable "key_vault_dns_zone_id" {
  description = "Private DNS zone privatelink.vaultcore.azure.net (networking module output)."
  type        = string
}

variable "operator_object_id" {
  description = "Entra ID user or group allowed to write this workload's secrets (in production: the pipeline)."
  type        = string
}

variable "operator_ip" {
  description = "Your public IP, set only during setup tasks (e.g. storing a secret). null = no public access."
  type        = string
  default     = null
}

variable "tags" {
  type = map(string)
}
