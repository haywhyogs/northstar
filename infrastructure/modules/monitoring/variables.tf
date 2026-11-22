variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "retention_days" {
  type    = number
  default = 30
}

variable "daily_quota_gb" {
  description = "Hard cap on log ingestion per day (cost guardrail). Logs beyond it are dropped until the next day."
  type        = number
  default     = 0.5
}

variable "local_authentication_enabled" {
  description = "Allow the workspace's shared keys. Off: only Entra ID identities can send or query logs. (Added in v1.1.0.)"
  type        = bool
  default     = false
}

variable "tags" {
  type = map(string)
}
