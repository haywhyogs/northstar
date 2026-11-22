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
