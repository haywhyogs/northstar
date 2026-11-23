# ADR-0011: GitHub Actions signs in to Azure as a managed identity, through OIDC

- **Status:** Accepted
- **Date:** 2026-11-23
- **Decided by:** Platform engineer (repository owner)

## Context
The deploy pipeline must push images to ACR and deploy to AKS. It must not hold any stored secret, and a job
must not be able to deploy to staging unless the reviewer approved it (ADR-0004, ADR-0006). Dev is destroyed after
every session, so anything the pipeline depends on must survive rebuilds.

## Decision
- **Identity:** a user-assigned managed identity, `id-northstar-github`, in the bootstrap resource group (never destroyed).
- **Sign-in:** OIDC federation. GitHub issues a short-lived token for each job; Entra ID swaps it for an Azure token
  only if the token's subject matches a federated credential. There is no client secret.
- **One federated credential per context** (subjects use GitHub's immutable format, `repo:<owner>@<owner-id>/<repo>@<repo-id>`,
  shortened below):
  - `repo:haywhyogs/northstar:ref:refs/heads/main`: the build job on `main`
  - `repo:haywhyogs/northstar:environment:dev`: deploys to `payments-dev`
  - `repo:haywhyogs/northstar:environment:staging`: deploys to `payments-staging`, only after the GitHub
    environment's required reviewer approves
- **Least privilege:** `Storage Blob Data Reader` on the state account (read Terraform outputs, never write state);
  in dev, `Reader` on the dev resource group (see resource names), `AcrPush` on the registry, `Azure Kubernetes Service Cluster User Role` on the cluster, and
  `Azure Kubernetes Service RBAC Writer` scoped to the pipeline's namespaces only. Dev grants these, so they are
  recreated with every rebuild.
- CI (pull requests) gets **no** Azure access at all.

## Alternatives considered
- **App registration / service principal with federated credentials:** common in companies; needs Entra ID permissions
  to create, and adds a second kind of identity to the platform.
- **Client secret stored in GitHub:** simple, but a long-lived secret that can leak and must be rotated.

## Consequences
- ✅ No secret to leak or rotate; every Azure action is tied to a specific repository, branch or environment.
- ✅ Editing the workflow can't bypass the staging approval: without the approved environment, no staging token is issued.
- ⚠️ The identity's object ID is stable, but its dev role assignments disappear on destroy and return on apply.
- 🔁 In production: separate identities per environment (and subscription), and pinning actions by commit SHA.

## References
- GitHub OIDC with Azure: https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-azure
- Workload identity federation: https://learn.microsoft.com/entra/workload-id/workload-identity-federation
- AKS Azure RBAC roles: https://learn.microsoft.com/azure/aks/manage-azure-rbac
