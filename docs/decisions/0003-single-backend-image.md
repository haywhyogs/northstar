# ADR-0003: One backend image, three processes

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Project owner

## Context
The backend has three jobs: the **API**, the **outbox dispatcher** and the **payment worker**. They share the same
database models and payment rules.

## Decision
Build **one** backend container image. Kubernetes runs it as **three separate Deployments**, each with a different start command.

## Alternatives considered
- **Three separate images/repos ("microservices")**: more realistic for big teams, but triples build, scan and deploy work.

## Consequences
- ✅ Fewer images to build, scan and tag. Shared code can't drift between services.
- ✅ Still independently scalable and killable (we can stop just the worker during the incident drill).
- ⚠️ A change to the API rebuilds the image the worker uses too.
