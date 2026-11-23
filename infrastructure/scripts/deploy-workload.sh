#!/usr/bin/env bash
# Deploy a workload's Kubernetes files to an environment, by hand (the Day 5 pipeline runs the same steps).
#   infrastructure/scripts/deploy-workload.sh payments dev <image-tag>
# Run from the repository root, after `terraform apply` and workload-setup.sh. Needs kubectl connected to the cluster.
# The image tag is the Git commit SHA the images were built from (build once, deploy the same image everywhere).
set -euo pipefail

app="${1:?usage: deploy-workload.sh <app> <env> <image-tag>}"
env="${2:?usage: deploy-workload.sh <app> <env> <image-tag>}"
tag="${3:?usage: deploy-workload.sh <app> <env> <image-tag>}"
prefix="${app//-/_}"
namespace="${app}-${env}"
overlay="apps/${app}/kubernetes/overlays/${env}"
tf() { terraform -chdir="infrastructure/environments/${env}" output -raw "$1"; }

echo "== Reading Azure addresses from Terraform outputs (${env})"
registry="$(tf acr_login_server)"
cat > "${overlay}/platform.env" <<ENV
DB_SERVER=$(tf sql_server_fqdn)
SERVICEBUS_NAMESPACE=$(tf servicebus_namespace).servicebus.windows.net
KEY_VAULT_URI=https://$(tf "${prefix}_key_vault_name").vault.azure.net/
ENV
cat > "${overlay}/deploy.env" <<ENV
IDENTITY_CLIENT_ID=$(tf "${prefix}_identity_client_id")
BACKEND_IMAGE=${registry}/${app}-backend:${tag}
WEB_IMAGE=${registry}/${app}-web:${tag}
ENV

echo "== Applying ${overlay} to namespace ${namespace}"
# A Job can't be changed once created, so remove the previous run before applying the new one.
kubectl delete job "${app}-migrate" -n "${namespace}" --ignore-not-found
kubectl apply -k "${overlay}"

echo "== Waiting for the database migration"
kubectl wait --for=condition=complete "job/${app}-migrate" -n "${namespace}" --timeout=10m

echo "== Waiting for each Deployment to become ready"
for deployment in $(kubectl get deployments -n "${namespace}" -o name); do
  kubectl rollout status "${deployment}" -n "${namespace}" --timeout=5m
done
kubectl get pods -n "${namespace}"
