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

variable "github_oidc_subject_prefix" {
  description = <<-EOT
    Start of the "subject" in the tokens GitHub Actions issues for this repository (ADR-0011).
    This repository uses GitHub's immutable format, which includes the owner's and repository's numeric IDs,
    so renaming them can't be used to impersonate it. Check it with:
      gh api repos/<owner>/<repo>/actions/oidc/customization/sub
  EOT
  type        = string
  default     = "repo:haywhyogs@101903693/northstar@1455456695"
}
