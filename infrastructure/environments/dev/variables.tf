variable "operator_ip" {
  description = "Your public IP, set only for setup tasks (ADR-0010). Leave unset to keep SQL and Key Vault private."
  type        = string
  default     = null
}

variable "alert_email" {
  description = "Where alerts are emailed (the on-call person). Set it in terraform.tfvars, which is gitignored."
  type        = string
  sensitive   = true # personal data: keep it out of plan output and logs
}
