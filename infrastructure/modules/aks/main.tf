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
    for_each = var.log_analytics_workspace_id == null ? [] : [1]
    content {
      log_analytics_workspace_id      = var.log_analytics_workspace_id
      msi_auth_for_monitoring_enabled = true
    }
  }

  tags = var.tags
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
