variable "name" {
  description = "Base name, e.g. northstar-dev. The cluster is called aks-<name>."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "subnet_id" {
  description = "Subnet the node joins (the networking module's AKS subnet)."
  type        = string
}

variable "acr_id" {
  description = "Container registry the nodes pull images from (AcrPull, Entra ID only)."
  type        = string
}

variable "admin_object_ids" {
  description = "Entra ID users or groups who get cluster-admin through Azure RBAC."
  type        = list(string)
}

variable "vm_size" {
  description = "Node size. B2ms = 2 vCPUs, 8 GB memory (ADR-0001 budget)."
  type        = string
  default     = "Standard_B2ms"
}

variable "node_count" {
  type    = number
  default = 1
}

variable "os_disk_size_gb" {
  description = "Node hard drive for the operating system, container images and logs."
  type        = number
  default     = 64
}

variable "kubernetes_version" {
  description = "null = the current AKS default version."
  type        = string
  default     = null
}

variable "log_analytics_workspace_id" {
  description = "Set to send container logs and metrics to Log Analytics (Container insights). null = off."
  type        = string
  default     = null
}

variable "tags" {
  type = map(string)
}
