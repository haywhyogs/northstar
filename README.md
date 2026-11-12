# Northstar: Secure Banking Workload Platform on Azure

A small but credible **Azure platform** that lets application teams provision, secure, deploy and monitor workloads
in a standard, repeatable way. It's a Cloud Platform Engineering / DevOps / SRE portfolio project.

> Northstar is fictional. All customers, accounts and balances are synthetic. No real money and no real banks.

## The business scenario
A fictional Canadian financial institution had every application team building its own infrastructure, pipelines,
network access, identity permissions and monitoring. The result was inconsistent environments, duplicated effort, security gaps and painful operations.

The **platform engineering team** introduces Northstar, a standard Azure workload platform. Application teams get:

- Approved, reusable **Terraform modules**
- One consistent **CI/CD pipeline** (GitHub Actions)
- **Passwordless** Azure authentication (OIDC for pipelines, workload identity for apps)
- **AKS** to run containers, **ACR** to store images
- **Private connectivity** to supported backend services
- **Central monitoring** of health, logs and failures
- A documented **onboarding** process

Two application teams consume the platform to prove it's reusable:

| Team | Workload | Purpose |
|---|---|---|
| Payments team | `apps/payments`: web frontend, Python API, payment worker, Azure SQL, Service Bus | The reliability scenario |
| Markets team | `apps/fx-rates`: tiny synthetic exchange-rate service | Onboarded using **only** the onboarding guide |

## The reliability scenario
Customer A sends $250 to Customer B. The payment worker goes down. The payment must stay **pending** (not falsely
"completed"), with no duplicate debit or credit, and complete correctly when the worker recovers. Monitoring must show what happened.
This is a proof of concept, not a production settlement system.

## Architecture: four layers
| Layer | What it does | Demonstrates |
|---|---|---|
| Developer workflow | Feature branches, pull requests, independent review, automated checks | Engineering collaboration |
| Delivery platform | GitHub Actions, Terraform, OIDC, image builds, approvals | DevOps automation |
| Azure foundation | VNet, AKS, ACR, identity, Key Vault, private endpoints and DNS | Cloud platform engineering |
| Workload and operations | API, worker, SQL, Service Bus, Azure Monitor | Reliability and troubleshooting |

Diagrams: [docs/architecture](docs/architecture/README.md) · Decisions: [docs/decisions](docs/decisions/README.md)

## Repository layout
| Path | Owner | Purpose |
|---|---|---|
| `infrastructure/bootstrap/` | Platform | Remote-state storage (created once) |
| `infrastructure/modules/` | Platform | Reusable building blocks: networking, aks, registry, database, messaging, identity, monitoring, workload |
| `infrastructure/environments/` | Platform | `dev` and `staging`: same modules, different settings |
| `.github/workflows/` | Platform | PR checks and reusable build/deploy workflows that every team calls |
| `apps/payments/` | Payments team | Web, backend (API + worker), Kubernetes manifests, tests |
| `apps/fx-rates/` | Markets team | Second workload, onboarded via the guide |
| `tests/smoke/` | Platform | Post-deployment smoke tests |
| `scripts/` | Platform | Helper scripts |
| `docs/` | Everyone | Architecture, decisions, onboarding, runbooks, incidents, learning notes |

## Budget
About $10 total. Free tiers first, AKS is short-lived, and one platform is applied. See [ADR-0001](docs/decisions/0001-budget-constrained-azure-design.md) and [ADR-0004](docs/decisions/0004-environment-strategy.md).

## Project status
Task-by-task tracker with next steps: **[PROGRESS.md](PROGRESS.md)**
