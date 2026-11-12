# ADR-0001: Budget-constrained Azure design

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Project owner

## Context
The original brief puts private endpoints on every service. In Azure, **Service Bus** and **Container Registry**
only support private endpoints on their **Premium** tiers, which cost hundreds of USD per month.
The project budget is **about $10 total**. We still need to demonstrate AKS, Terraform, CI/CD, messaging,
identity and observability.

## Decision
| Component | Choice |
|---|---|
| AKS | Free control-plane tier, **1 small node**. Created for working sessions and **destroyed with Terraform** afterwards |
| Azure SQL Database | **Free offer**, configured to pause (not bill) when the monthly free allowance is used up |
| Service Bus | **Basic** tier, public endpoint, **Entra ID auth only** (local/SAS keys disabled where supported) |
| Container Registry | **Basic** tier, public endpoint, Entra ID auth, AKS pulls via `AcrPull` role |
| Key Vault | Standard, with a **private endpoint** |
| Azure SQL private connectivity | **Private endpoint** + private DNS zone. Public network access disabled once the pipeline no longer needs it |
| Networking | One VNet with an AKS subnet and a private endpoint subnet (VNets themselves are free; private endpoints cost about a cent an hour each, so they're created and destroyed with the platform) |
| Observability | Log Analytics + workspace-based Application Insights with a **daily ingestion cap** |
| Cost guardrails | Azure budget alerts at $5 and $10, created on Day 1, before any other resource |

Every price is to be verified in the Azure Pricing Calculator (Canada Central) before provisioning on Day 4.

## Alternatives considered
- **Premium tiers with private endpoints everywhere**: closest to a real bank, but roughly 100× over budget.
- **Local Kubernetes only (kind/minikube)**: free, but loses the AKS and Azure identity learning outcomes.
- **Keep AKS running 24/7**: simpler, but adds roughly $1–2 per day for no learning benefit.

## Consequences
- ✅ Learning outcomes are preserved at roughly $3–10.
- ✅ Recreating AKS each session is a real-world test that our Terraform is repeatable.
- ⚠️ Service Bus and ACR are reachable over the public internet, protected by identity rather than network isolation.
- ⚠️ Service Bus Basic has no built-in duplicate detection. That's fine, because our database idempotency is the real protection (ADR-0002).
- 🏦 **In production** we'd use Premium tiers with private endpoints, disable public network access, and run separate staging/production subscriptions.

## References
- Azure SQL Database free offer: https://learn.microsoft.com/azure/azure-sql/database/free-offer
- Service Bus tiers: https://learn.microsoft.com/azure/service-bus-messaging/service-bus-premium-messaging
- Service Bus private endpoints (Premium): https://learn.microsoft.com/azure/service-bus-messaging/private-link-service
- ACR service tiers: https://learn.microsoft.com/azure/container-registry/container-registry-skus
- AKS pricing tiers: https://learn.microsoft.com/azure/aks/free-standard-pricing-tiers
- Azure budgets: https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-acm-create-budgets
