# aks module: changelog

## v1.0.0
- AKS cluster (Free tier, one B2ms node), Azure CNI Overlay with Cilium network policy, Standard load balancer for outbound traffic.
- OIDC issuer and workload identity on. Entra ID only: local accounts off, Azure RBAC for Kubernetes.
- AcrPull for the node identity, Network Contributor on the subnet, Cluster Admin for `admin_object_ids`.
- Optional Container insights (`log_analytics_workspace_id`).
