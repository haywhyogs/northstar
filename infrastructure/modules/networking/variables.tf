variable "name" {
  description = "Base name, e.g. northstar-dev."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "address_space" {
  description = "VNet range. Must not overlap other environments' VNets (they may be peered later)."
  type        = string
}

variable "aks_subnet_prefix" {
  description = "Subnet for AKS nodes and pods."
  type        = string
}

variable "private_endpoints_subnet_prefix" {
  description = "Subnet for private endpoints (Azure SQL, Key Vault)."
  type        = string
}

variable "tags" {
  type = map(string)
}
