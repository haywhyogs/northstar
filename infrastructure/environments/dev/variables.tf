variable "operator_ip" {
  description = "Your public IP, set only for setup tasks (ADR-0010). Leave unset to keep SQL and Key Vault private."
  type        = string
  default     = null
}
