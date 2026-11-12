# Repository structure: what each folder is for, and where new things go

## The organising idea
The repo is split by three questions, in this order:
1. **Who owns it?** The platform team (shared foundation) or an application team (one app)
2. **Which tool reads it?** Terraform, Kubernetes, GitHub Actions, Docker, or humans (docs)
3. **Which environment does it affect?** `dev` or `staging`

Think of a **shopping centre**. The **platform team is the landlord**: building, power, security, CCTV.
Each **application team is a shop tenant**: they fit out their own unit, but plug into the landlord's power and security.

## The tree, explained

```
northstar/
├── .github/workflows/        LANDLORD · CI/CD pipelines (GitHub only looks for workflows here)
│
├── infrastructure/           LANDLORD · Terraform: everything created in Azure
│   ├── bootstrap/            Creates the storage account that holds Terraform's own state.
│   │                         Chicken-and-egg: it runs ONCE, before the remote state exists.
│   ├── modules/              Reusable LEGO bricks. Never applied on their own.
│   │   ├── networking/       VNet, subnets, private DNS zones
│   │   ├── aks/              The Kubernetes cluster
│   │   ├── registry/         Azure Container Registry
│   │   ├── database/         Azure SQL server + databases + private endpoint
│   │   ├── messaging/        Service Bus namespace + queues
│   │   ├── identity/         Managed identities, role assignments, Key Vault
│   │   ├── monitoring/       Log Analytics, Application Insights, alerts
│   │   └── workload/         "Onboard an app": its identity, federated credential, permissions
│   └── environments/         The assembled models. You run terraform plan/apply HERE.
│       ├── dev/              Calls the modules with dev settings (own state file)
│       └── staging/          Calls the SAME modules with staging settings (own state file)
│
├── apps/                     TENANTS · one folder per application team
│   ├── payments/             Payments team
│   │   ├── web/              React frontend (what customers see)
│   │   ├── backend/          Python API + dispatcher + worker, their tests, Dockerfile, DB migrations
│   │   └── kubernetes/
│   │       ├── base/         YAML that's identical in every environment
│   │       │   ├── web/  api/  worker/
│   │       └── overlays/     Only the DIFFERENCES per environment
│   │           ├── dev/      e.g. 1 replica, dev database name, image tag
│   │           └── staging/  e.g. 2 replicas, staging database name
│   └── fx-rates/             Markets team (onboarded on Day 7 using only the guide)
│
├── tests/smoke/              LANDLORD · "is the deployed thing alive?" checks used after ANY deployment
├── scripts/                  Helper scripts (seed data, incident-drill helpers)
├── docs/                     EVERYONE
│   ├── architecture/         Diagrams: how the pieces fit
│   ├── decisions/            ADRs: WHY we chose things
│   ├── onboarding/           How a new team uses the platform
│   ├── runbooks/             Step-by-step "how to fix X" for on-call engineers
│   ├── incidents/            Post-incident reports (what happened, why, prevention)
│   └── learning-notes/       Your study notes and explanations
├── README.md                 Front door of the project
└── .gitignore                Files Git must never upload
```

Every Terraform module will contain the same three files:
`main.tf` (what to build) · `variables.tf` (inputs it accepts) · `outputs.tf` (values it hands back, e.g. the subnet ID that AKS needs).

`.gitkeep` files are empty placeholders. Git doesn't track empty folders, so they disappear once real files arrive.

## Is this standard?
| Part | How standard | Source |
|---|---|---|
| `.github/workflows/` | **Mandatory**: GitHub only runs workflows from this path | [GitHub docs](https://docs.github.com/actions/writing-workflows/about-workflows) |
| Terraform `modules/` vs `environments/` | **Recommended pattern**: reusable *child modules* called by per-environment *root modules* | [HashiCorp: module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure) |
| Kubernetes `base/` + `overlays/` | **The official Kustomize pattern** | [Kubernetes: Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/) |
| `docs/decisions/` (ADRs) | **Widely used convention**, also recommended by Microsoft | [Azure Well-Architected: ADRs](https://learn.microsoft.com/azure/well-architected/architect-role/architecture-decision-record) |
| `apps/<team>/` in one repo | **Common monorepo convention**, but not an official standard. Some companies call it `services/`; others use one repo per team | Our choice: ADR-0005 |

## "Where does it go?" cheat sheet
| I want to… | Put it in |
|---|---|
| Add an API endpoint or change payment logic | `apps/payments/backend/` |
| Change the customer website | `apps/payments/web/` |
| Run 2 copies of the API in staging only | `apps/payments/kubernetes/overlays/staging/` |
| Change a setting for the API in **every** environment | `apps/payments/kubernetes/base/api/` |
| Add a new Azure service every team can use (e.g. Redis) | New module in `infrastructure/modules/`, then call it from `infrastructure/environments/*` |
| Make the dev cluster's node bigger | `infrastructure/environments/dev/` (a variable value), **not** the module |
| Give an app access to a new Azure resource | `infrastructure/modules/workload/` (or its call in `environments/*`) |
| Onboard a new team's app | `apps/<new-app>/` + a `workload` module call + call the reusable workflow |
| Add a pipeline check for everyone | `.github/workflows/` |
| Explain why we chose something | New ADR in `docs/decisions/` |
| Write "how to fix the worker when it's down" | `docs/runbooks/` |
