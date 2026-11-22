# ADR-0008: Terraform remote state in Azure Storage, created by a bootstrap configuration

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Platform engineer (repository owner)

## Context
Terraform records what it manages in a state file. Shared environments need that state stored centrally, protected,
locked during changes, and recoverable. The storage for it must exist before any environment can use it.

## Decision
- A separate configuration, `infrastructure/bootstrap`, creates the state storage once. Its own small state stays local
  on the operator's machine (git-ignored).
- One storage account in its own resource group (`rg-northstar-tfstate`), container `tfstate`, one blob per environment
  (`dev.tfstate`, `staging.tfstate`).
- **Entra ID only:** account keys are disabled; the backend uses `use_azuread_auth = true`. Humans and the CI/CD identity get
  `Storage Blob Data Contributor` on this account only.
- **Recovery:** blob versioning plus 7-day soft delete for blobs and containers.
- **Locking:** the azurerm backend's built-in blob lease.

## Alternatives considered
- **Create the storage with `az` CLI commands:** quick, but untracked and easy to misconfigure (e.g. forgetting versioning).
- **HCP Terraform (Terraform Cloud):** managed state and runs, but adds another platform and account outside Azure.
- **State in Git:** never. State can contain secrets and has no locking.

## Consequences
- ✅ Every environment shares one hardened, recoverable backend; no secrets needed to reach it.
- ✅ State lives outside the environments' resource groups, so `terraform destroy` of an environment can't delete its own state.
- ⚠️ The bootstrap's local state is a single copy. Losing it is recoverable (`terraform import`) and doesn't affect environments.
- ⚠️ The storage account keeps a public endpoint (identity-protected) so laptops and GitHub-hosted runners can reach it.
- 🔁 In production: ZRS/GRS replication, a delete lock, a private endpoint with self-hosted runners, and separate state
  accounts per subscription.

## References
- Store Terraform state in Azure Storage: https://learn.microsoft.com/azure/developer/terraform/store-state-in-azure-storage
- azurerm backend: https://developer.hashicorp.com/terraform/language/backend/azurerm
- Blob versioning: https://learn.microsoft.com/azure/storage/blobs/versioning-overview
