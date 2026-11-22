# ADR-0009: Version Terraform modules with Git tags; environments pin a tag

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Platform engineer (repository owner)

## Context
Environments referenced modules by folder path (`../../modules/networking`), so any module change reached every environment on its
next plan. A shared module must be changeable without affecting staging (or production) until the change is proven.

## Decision
- Each module is released with an annotated Git tag: `modules/<module>/vMAJOR.MINOR.PATCH`, e.g. `modules/networking/v1.0.0`.
- Environments pin a tag in the module source:
  `git::https://github.com/haywhyogs/northstar.git//infrastructure/modules/networking?ref=modules/networking/v1.0.0`
- Semantic versioning: PATCH = fix, MINOR = backwards-compatible addition, MAJOR = breaking change (callers must change).
- Rollout: change the module in a PR → merge → tag the new version → bump **dev** in a PR → verify → bump **staging** in a later PR.

## Alternatives considered
- **Folder paths:** simplest, but every environment gets every change at once.
- **Private module registry (HCP Terraform):** proper version constraints (`~> 1.2`) and a catalogue, but another platform to run.
- **A separate repository per module:** strong isolation, but heavy for one small team.

## Consequences
- ✅ dev and staging can run different module versions; staging only moves when its pin is bumped (reviewed in a PR).
- ✅ The tag history is a release log of the platform.
- ⚠️ Two steps per change (merge, then tag and bump). Local module edits aren't used by environments until tagged.
- ⚠️ Tags can be moved or deleted by anyone with write access; protect `modules/*` tags with a tag ruleset.

## References
- Module sources (Git, `ref`): https://developer.hashicorp.com/terraform/language/modules/sources#generic-git-repository
- Semantic Versioning: https://semver.org/
- GitHub tag rulesets: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
