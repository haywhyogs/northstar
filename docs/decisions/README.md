# Architecture Decision Records (ADRs)

An ADR is a short note that records **one important decision**: the context, what we chose, the alternatives and the consequences.
It lets anyone (a new engineer, an auditor, a reviewer) see *why* the platform looks the way it does.

| # | Decision | Status |
|---|---|---|
| [0001](0001-budget-constrained-azure-design.md) | Budget-constrained Azure design (~$10 total) | Accepted |
| [0002](0002-transactional-outbox-and-idempotency.md) | Transactional outbox + idempotent worker for payments | Accepted |
| [0003](0003-single-backend-image.md) | Payments backend: one image, three processes | Accepted |
| [0004](0004-environment-strategy.md) | One applied platform, namespace environments, brief staging proof | Accepted |
| [0005](0005-multi-team-repository-layout.md) | Repository layout for a multi-team platform | Accepted |
| [0006](0006-source-control-and-review-model.md) | Source control, authentication and two-account review model | Accepted |
| [0007](0007-customer-session-tokens.md) | Customer sessions use short-lived signed tokens (JWT) | Accepted |
| [0008](0008-terraform-remote-state.md) | Terraform remote state in Azure Storage, created by a bootstrap configuration | Accepted |
| [0009](0009-module-versioning-with-git-tags.md) | Version Terraform modules with Git tags; environments pin a tag | Accepted |
| [0010](0010-private-endpoints-and-operator-access.md) | Private endpoints, per-workload resources, temporary operator IP access | Accepted |

Template: copy [0000-template.md](0000-template.md).
