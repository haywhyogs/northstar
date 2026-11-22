variable "location" {
  description = "Azure region for the state storage."
  type        = string
  default     = "canadacentral"
}

variable "owner" {
  description = "Value of the 'owner' tag (a team, not a person)."
  type        = string
  default     = "platform-team"
}

variable "soft_delete_days" {
  description = "How long deleted or overwritten state blobs can be recovered."
  type        = number
  default     = 7
}
