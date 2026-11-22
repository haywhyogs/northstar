# Environment: dev

The platform foundation for dev: resource group, VNet with NSG-protected subnets, Log Analytics + Application Insights,
container registry, Service Bus namespace and Azure SQL logical server. AKS and per-team workloads are added on top.

```bash
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform init -backend-config=backend.hcl   # state: dev.tfstate in the bootstrap storage account
terraform plan -out tfplan                  # review before applying
terraform apply tfplan
```
Environment-specific settings live in the `locals` block of `main.tf`; staging uses the same modules with different values.
