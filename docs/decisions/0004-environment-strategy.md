# ADR-0004: One applied platform, namespace environments, brief staging proof

- **Status:** Accepted
- **Date:** 2026-11-10
- **Decided by:** Project owner

## Context
The brief asks for `dev` and `staging` environments, with staging as the production-like one that needs approval.
Two full copies of the platform (two AKS clusters, two SQL servers and so on) running every day would roughly double the cost and break the ~$10 budget.

## Decision
1. **Terraform:** `infrastructure/environments/dev` and `infrastructure/environments/staging` both exist. They use the **same modules**
   and differ only in variables (names, sizes, tags). Both are checked with `terraform validate` and `terraform plan`.
2. **Day to day, only `dev` is applied**: one platform with one AKS cluster, one SQL server, one Service Bus namespace.
3. **Application environments are Kubernetes namespaces** on that cluster: `<app>-dev` and `<app>-staging`.
   Each app environment gets its own database, queue and workload identity. Deploying to `*-staging` requires a
   **manual approval** from the reviewer account.
4. **Day 7 timeboxed proof (if on schedule):** `terraform apply` `environments/staging` as a fully separate platform,
   deploy the **same image SHA**, run smoke tests, capture evidence, then `terraform destroy`.
   Estimated cost: under $1 for under an hour (one small node, load balancer, a few private endpoints, free-offer SQL).
   To verify in the Pricing Calculator, and check the regional vCPU quota allows two clusters.
5. **Production** is described in docs as "staging, but in its own subscription with stricter policies". It's not built.

## Alternatives considered
- **Two platforms running all week**: true isolation, but roughly double the cost for no extra learning.
- **Namespaces only, no separate staging apply**: cheapest, but never proves the Terraform environment pattern really works.

## Consequences
- ✅ Daily cost stays at one small platform.
- ✅ The approval gate and promotion of the same image are demonstrated every day.
- ✅ The Day 7 proof shows "same modules + different variables = an identical, isolated environment", which is the core claim of a platform.
- ⚠️ `dev` and `staging` namespaces share one node and one cluster. A misbehaving dev workload could affect staging.
  Mitigated with resource limits and separate identities; real production would never share a cluster with dev.
