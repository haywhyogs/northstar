# Bootstrap: Terraform remote state

Creates the storage that every other Terraform environment uses for its state (ADR-0008). Run **once**, by a platform engineer.

| Resource | Setting | Why |
|---|---|---|
| `rg-northstar-tfstate` | Separate resource group | Destroying an environment never touches its state |
| Storage account (`stnorthstartf…`) | Standard LRS, TLS 1.2, no public blobs | Cheap (cents per month) and locked down |
| | **Account keys disabled** | Only Entra ID identities with an RBAC role can read or write state |
| | **Blob versioning + 7-day soft delete** | A corrupted or deleted state file can be restored |
| `tfstate` container | Private | One blob per environment, e.g. `dev.tfstate` |
| Role assignment | Storage Blob Data Contributor for the operator | Lets `terraform init` authenticate with Entra ID |

State locking is built in: the azurerm backend takes a **blob lease** during `plan`/`apply`, so two runs can't write at once.

## Run it
```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform init
terraform plan -out tfplan
terraform apply tfplan
terraform output backend_config_example
```

This configuration's own state is **local** (`terraform.tfstate`, git-ignored): it can't store its state in a backend that doesn't exist yet.
If that file is lost, re-import the resources with `terraform import` or recreate the backend; the environments' state is unaffected.
