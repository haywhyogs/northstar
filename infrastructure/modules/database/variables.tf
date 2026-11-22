variable "name" {
  description = "Globally unique logical server name."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "entra_admin_login" {
  description = "Display name of the Entra ID administrator (in production: a group)."
  type        = string
}

variable "entra_admin_object_id" {
  description = "Object ID of that user or group."
  type        = string
}

variable "tags" {
  type = map(string)
}

variable "private_endpoint" {
  description = "Subnet and private DNS zone (privatelink.database.windows.net) for the server's private endpoint. null = none."
  type = object({
    subnet_id   = string
    dns_zone_id = string
  })
  default = null
}

variable "operator_ip" {
  description = "Your public IP, set only during setup tasks (e.g. granting database access). null = no public access."
  type        = string
  default     = null
}
