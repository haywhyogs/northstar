# ADR-0006: Source control, authentication and two-account review model

- **Status:** Accepted
- **Date:** 2026-11-10
- **Decided by:** Project owner

## Context
The brief requires genuine, independent pull-request review and a manual approval before the production-like deployment.
GitHub doesn't let the author of a pull request approve their own PR, so a second person (account) is needed.

## Decision
- **Repository:** public, owned by the **main account** (the engineer).
- **Second account:** added as a **collaborator with Write access**. It reviews and approves **in the browser**
  (a separate browser profile or private window). It doesn't clone the repo, push code or need SSH keys.
- **Git authentication (main account):** **SSH** with an Ed25519 key stored in the macOS keychain.
  The `gh` CLI is also logged in, for GitHub API work (repos, PRs), with SSH as its Git protocol.
- **Commit identity:** GitHub's no-reply email, so a real address isn't published in a public repo.
- **Main branch ruleset:** changes only via pull request · 1 approving review · required status checks pass ·
  no force-push or deletion · **no bypass, including for the repository owner**. Otherwise the owner could skip review and the demo wouldn't be genuine.
- **Deployment environment `staging`:** required reviewer = second account, with "prevent self-review" enabled.
- **Branching:** short-lived `feature/<description>` branches, squash-merged into `main`.

## Alternatives considered
- **HTTPS with a personal access token or the `gh` credential helper**: also valid. SSH was chosen because keys never expire into a stored token and are the same mechanism used for servers.
- **A GitHub organization with teams and CODEOWNERS**: more realistic for many teams. Possible later; not needed to prove review.

## Consequences
- ✅ Every merge to `main` and every staging deployment has a recorded, independent approval.
- ⚠️ One human controls both accounts. That's acceptable for a portfolio, and it's stated honestly in the docs.

## References
- SSH keys for GitHub: https://docs.github.com/authentication/connecting-to-github-with-ssh
- Rulesets: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- Deployment environments: https://docs.github.com/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
