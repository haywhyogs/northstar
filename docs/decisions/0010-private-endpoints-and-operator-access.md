# ADR-0010: Private endpoints for data and secrets; per-workload resources; temporary operator IP access

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Platform engineer (repository owner)

## Context
Azure SQL (customer data) and Key Vault (secrets) must not be reachable from the internet. Only pods in AKS need them.
Two one-off setup tasks still need a human: granting a workload's identity access to its database (a SQL command),
and storing the workload's JWT signing key in its Key Vault. There is no network path from a laptop into the VNet
(no VPN, no self-hosted runners) within the budget (ADR-0001).

## Decision
- **Private endpoints** for the SQL server and every workload Key Vault, in the private endpoint subnet, with private DNS zones
  (`privatelink.database.windows.net`, `privatelink.vaultcore.azure.net`) linked to the VNet. Public network access is off.
- **Per-workload resources** (workload module): each app gets its own user-assigned identity (workload identity), database,
  Service Bus queues and Key Vault. Teams share the cluster, SQL server and Service Bus namespace, but not data or secrets.
- **Operator access:** an optional `operator_ip` variable opens SQL and Key Vault to that single public IP, for setup tasks only.
  Unset (the default), both are private-endpoint only. Secrets are written by the operator with `az`, never through Terraform or Git.
- The database runs on the **Azure SQL free offer** (serverless, auto-pause when the monthly allowance is used up), set through the
  `azapi` provider because `azurerm` has no setting for it.

## Alternatives considered
- **Fully private, setup from a pod inside the cluster:** no public door at all, but more manual steps. The production direction.
- **Self-hosted CI/CD runners or a VPN in the VNet:** the production answer; costs a VM running all the time.
- **One shared database and Key Vault for all teams:** cheaper, but one team's mistake or breach exposes the others.

## Consequences
- ✅ No public path to data or secrets in normal operation; three layers: network (private endpoint + NSG), identity (Entra ID roles) and DNS.
- ⚠️ While `operator_ip` is set, the public endpoint is open to that IP. Set it only for the task, then remove it and re-apply.
- ⚠️ Each private endpoint costs about $0.01/hour; each workload adds one (its Key Vault).
- ⚠️ The workload identity has `db_ddladmin` so the migrate job can change the schema. Production: a separate migration identity.
- 🔁 In production: self-hosted runners in the VNet, no operator IP, and purge protection on Key Vault.

## References
- Private endpoint DNS zone values: https://learn.microsoft.com/azure/private-link/private-endpoint-dns
- AKS workload identity: https://learn.microsoft.com/azure/aks/workload-identity-overview
- Azure SQL free offer: https://learn.microsoft.com/azure/azure-sql/database/free-offer
