# Onboarding a new application team to Northstar

> Draft outline. Written properly on Day 7 and tested by onboarding the Markets team's `fx-rates` app **using only this guide**.

1. **What the platform gives you**: cluster, registry, identity, networking, monitoring, pipeline
2. **Where the reusable Terraform modules live**: `infrastructure/modules/` (the `workload` module onboards your app)
3. **Configure your environment**: add your app to `infrastructure/environments/<env>`
4. **Add your app**: `apps/<your-app>/` with a Dockerfile and `kubernetes/base` + `overlays/<env>`
5. **Branch and pull request workflow**: `feature/*` → PR → checks → review → merge
6. **What the automated checks do, and how to read a failure**
7. **Deploying**: call the reusable workflow; dev is automatic, staging needs approval
8. **Monitoring**: where your logs, metrics and alerts are
9. **Troubleshooting**: links to runbooks
