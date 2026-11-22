# Environment: staging

The platform foundation for staging: resource group, VNet with NSG-protected subnets, Log Analytics + Application Insights,
container registry, Service Bus namespace and Azure SQL logical server. AKS and per-team workloads are added on top.

```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform init -backend-config=backend.hcl   # state: staging.tfstate in the bootstrap storage account
terraform plan -out tfplan                  # review before applying
terraform apply tfplan
```
Environment-specific settings live in the `locals` block of `main.tf`; dev uses the same modules with different values.

Applied only for the timeboxed staging proof (ADR-0004). Module versions may lag dev's: staging moves to a new module tag only after dev has run it.
