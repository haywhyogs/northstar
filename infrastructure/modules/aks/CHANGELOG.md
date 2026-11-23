# aks module: changelog

## v1.1.0
- Default `vm_size` is now `Standard_D2as_v7` (B2ms isn't allowed for AKS in our subscription in canadacentral).
  Callers relying on the default get a node pool rotation; callers that set `vm_size` see no change.
- Declared `upgrade_settings` (Azure's defaults), which removes a change that appeared on every plan.

## v1.0.0
- AKS cluster (Free tier, one B2ms node), Azure CNI Overlay with Cilium network policy, Standard load balancer for outbound traffic.
- OIDC issuer and workload identity on. Entra ID only: local accounts off, Azure RBAC for Kubernetes.
- AcrPull for the node identity, Network Contributor on the subnet, Cluster Admin for `admin_object_ids`.
- Optional Container insights (`log_analytics_workspace_id`).
