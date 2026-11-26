# aks module: changelog

## v1.3.0
- Fix: v1.2.0 failed to plan on a fresh build ("Invalid count argument"), because whether to create the data collection
  rule depended on the workspace ID, which isn't known until the workspace is created.
- New `container_insights_enabled` (true/false, default false) switches Container insights on.
  **Callers that set `log_analytics_workspace_id` must now also set `container_insights_enabled = true`.**

## v1.2.0
- Container insights now actually collects data: adds the data collection rule (DCR) and its association to the
  cluster when `log_analytics_workspace_id` is set. Without them the agent ran but sent nothing.
- Cost-optimised collection: ContainerLogV2 only (no legacy ContainerLog), 5-minute interval, `kube-system` excluded.
- No change for callers that leave `log_analytics_workspace_id` unset.

## v1.1.0
- Default `vm_size` is now `Standard_D2as_v7` (B2ms isn't allowed for AKS in our subscription in canadacentral).
  Callers relying on the default get a node pool rotation; callers that set `vm_size` see no change.
- Declared `upgrade_settings` (Azure's defaults), which removes a change that appeared on every plan.

## v1.0.0
- AKS cluster (Free tier, one B2ms node), Azure CNI Overlay with Cilium network policy, Standard load balancer for outbound traffic.
- OIDC issuer and workload identity on. Entra ID only: local accounts off, Azure RBAC for Kubernetes.
- AcrPull for the node identity, Network Contributor on the subnet, Cluster Admin for `admin_object_ids`.
- Optional Container insights (`log_analytics_workspace_id`).
