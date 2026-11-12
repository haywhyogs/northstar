# ADR-0005: Repository layout for a multi-team platform

- **Status:** Accepted
- **Date:** 2026-11-10
- **Decided by:** Project owner

## Context
Northstar must prove it's a **platform**, not one person's app. A second team (Markets, `fx-rates`) will onboard
using only the onboarding guide. The layout must make it obvious what the platform owns and what each team owns.

## Decision
- `infrastructure/` and `.github/workflows/` are owned by the **platform team**.
  - `infrastructure/modules/workload` is a small "onboard an app" module: it creates an app's managed identity,
    federated credential and role assignments.
  - A **reusable workflow** (`workflow_call`) builds, scans, pushes and deploys any app. Teams call it instead of writing their own.
- Each team owns one folder under `apps/<app>/`, containing its source, Dockerfile(s), `kubernetes/base` and `kubernetes/overlays/<env>`.
- `tests/smoke/` holds platform-level smoke tests that any deployed app can be checked with.
- One repository (a "monorepo") for simplicity.

## Alternatives considered
- **The original single-app layout** (`frontend/`, `backend/`, `kubernetes/` at the root): fine for one app, but doesn't show team ownership.
- **One repo per team, plus a platform repo**: closer to large enterprises, but adds cross-repo workflow permissions and setup time.

## Consequences
- ✅ Onboarding a team = add `apps/<name>/`, call the workload module, call the reusable workflow.
- ⚠️ In a monorepo, CI must only rebuild what changed (path filters).
- 🏦 In production, CODEOWNERS (or separate repos) would enforce team ownership of each folder.
