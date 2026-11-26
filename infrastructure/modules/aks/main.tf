# One small AKS cluster per environment. Teams share it; each team gets its own namespaces.
# Identity is Entra ID only: no local admin account, Kubernetes permissions come from Azure RBAC.

data "azurerm_client_config" "current" {}

resource "azurerm_kubernetes_cluster" "this" {
  name                = "aks-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  dns_prefix          = "aks-${var.name}"
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Free" # no uptime SLA: fine for dev/staging (production: Standard)

  default_node_pool {
    name                        = "system"
    vm_size                     = var.vm_size
    node_count                  = var.node_count
    vnet_subnet_id              = var.subnet_id
    os_disk_size_gb             = var.os_disk_size_gb
    os_disk_type                = "Managed"
    temporary_name_for_rotation = "systemtmp" # lets Terraform change the VM size without destroying the cluster
    tags                        = var.tags

    # Azure's defaults, declared so Terraform doesn't show a change on every plan.
    upgrade_settings {
      max_surge                     = "10%" # add a temporary extra node during upgrades
      drain_timeout_in_minutes      = 0
      node_soak_duration_in_minutes = 0
    }
  }

  # The cluster's own identity, used by AKS to manage Azure resources (load balancer, node NICs).
  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay" # nodes get VNet IPs, pods get IPs from pod_cidr: saves VNet addresses
    network_data_plane  = "cilium"
    network_policy      = "cilium" # lets us write Kubernetes NetworkPolicies between namespaces
    pod_cidr            = "10.244.0.0/16"
    service_cidr        = "10.0.0.0/16" # never overlaps the VNets (10.20.x dev, 10.30.x staging)
    dns_service_ip      = "10.0.0.10"
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer" # nodes reach the internet (ACR, Service Bus) through the load balancer's public IP
  }

  # Workload identity: pods get their own Entra ID identity, without secrets (Day 4).
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # Entra ID sign-in only. kubectl needs kubelogin.
  local_account_disabled = true
  azure_active_directory_role_based_access_control {
    tenant_id          = data.azurerm_client_config.current.tenant_id
    azure_rbac_enabled = true
  }

  dynamic "oms_agent" {
    for_each = var.container_insights_enabled ? [1] : []
    content {
      log_analytics_workspace_id      = var.log_analytics_workspace_id
      msi_auth_for_monitoring_enabled = true
    }
  }

  tags = var.tags
}

# ---------- Container insights: what the agent collects and where it sends it ----------
# The add-on above only installs the agent (the ama-logs pods). With managed-identity auth, the agent also needs a
# data collection rule (DCR) linked to the cluster. The portal and CLI create these for you; Terraform doesn't.
# Based on Microsoft's Terraform template for Container insights (Microsoft Learn: "Enable monitoring for AKS").
locals {
  # A plain true/false that Terraform knows while planning. Testing the workspace ID instead fails on a fresh build:
  # the workspace doesn't exist yet, so its ID is "known after apply" and `count` can't be decided (v1.2.0 bug).
  container_insights = var.container_insights_enabled

  # Cost-optimised: no legacy ContainerLog table (ContainerLogV2 replaces it), and samples every 5 minutes.
  container_insights_streams = [
    "Microsoft-ContainerLogV2",     # what our containers print (our JSON logs)
    "Microsoft-KubeEvents",         # what `kubectl describe` shows: probe failures, OOMKilled, image pulls
    "Microsoft-KubePodInventory",   # which pods exist, their status and restarts
    "Microsoft-KubeNodeInventory",  # node status
    "Microsoft-KubeServices",       # services
    "Microsoft-KubeMonAgentEvents", # the agent's own health
    "Microsoft-InsightsMetrics",    # CPU and memory per pod/container
    "Microsoft-ContainerInventory", # container images and states
    "Microsoft-ContainerNodeInventory",
    "Microsoft-Perf", # node and container performance counters
  ]
}

resource "azurerm_monitor_data_collection_rule" "container_insights" {
  count               = local.container_insights ? 1 : 0
  name                = "MSCI-${var.location}-aks-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location # same region as the workspace
  description         = "Container insights for aks-${var.name}"
  tags                = var.tags

  destinations {
    log_analytics {
      workspace_resource_id = var.log_analytics_workspace_id
      name                  = "ciworkspace"
    }
  }

  data_flow {
    streams      = local.container_insights_streams
    destinations = ["ciworkspace"]
  }

  data_sources {
    extension {
      name           = "ContainerInsightsExtension"
      extension_name = "ContainerInsights"
      streams        = local.container_insights_streams
      extension_json = jsonencode({
        dataCollectionSettings = {
          interval               = "5m"      # Microsoft's cost-optimised preset (default is 1m)
          namespaceFilteringMode = "Exclude" # skip the cluster's own system namespace: noisy and not ours
          namespaces             = ["kube-system"]
          enableContainerLogV2   = true
        }
      })
    }
  }
}

# Links the rule to the cluster. Without this, the agent runs but collects nothing (what we saw on 2026-11-25).
resource "azurerm_monitor_data_collection_rule_association" "container_insights" {
  count                   = local.container_insights ? 1 : 0
  name                    = "ContainerInsightsExtension" # the name Azure expects for this association
  target_resource_id      = azurerm_kubernetes_cluster.this.id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.container_insights[0].id
  description             = "Deleting this association stops Container insights data collection for this cluster."
}

# AKS needs to manage the node's network card in our subnet.
resource "azurerm_role_assignment" "cluster_network" {
  scope                = var.subnet_id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.this.identity[0].principal_id
}

# The node (kubelet identity) pulls images from ACR. No registry password.
resource "azurerm_role_assignment" "acr_pull" {
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# Platform admins get full Kubernetes access through Azure RBAC.
resource "azurerm_role_assignment" "admins" {
  for_each             = toset(var.admin_object_ids)
  scope                = azurerm_kubernetes_cluster.this.id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = each.value
}
