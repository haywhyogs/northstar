#!/usr/bin/env bash
# Deploy a workload slice's Kubernetes files. Used by hand and by the deploy pipeline (same steps).
#   infrastructure/scripts/deploy-workload.sh payments dev <image-tag>
#   infrastructure/scripts/deploy-workload.sh payments staging <image-tag>
# Run from the repository root, with kubectl connected to the cluster and read access to Terraform state.
# The image tag is the Git commit SHA the images were built from (build once, deploy the same image everywhere).
# PLATFORM selects the Terraform folder that holds the cluster (default: dev; staging slices live there too, ADR-0004).
set -euo pipefail

app="${1:?usage: deploy-workload.sh <app> <env> <image-tag>}"
env="${2:?usage: deploy-workload.sh <app> <env> <image-tag>}"
tag="${3:?usage: deploy-workload.sh <app> <env> <image-tag>}"
platform="${PLATFORM:-dev}"
namespace="${app}-${env}"
overlay="apps/${app}/kubernetes/overlays/${env}"
tf() { terraform -chdir="infrastructure/environments/${platform}" output "$@"; }

echo "== Reading Azure addresses from Terraform outputs (${platform})"
workload="$(tf -json workloads | jq -e --arg ns "$namespace" '.[$ns]')" \
  || { echo "No workload '${namespace}' in the ${platform} platform's outputs"; exit 1; }
field() { jq -r --arg f "$1" '.[$f]' <<<"$workload"; }
registry="$(tf -raw acr_login_server)"

cat > "${overlay}/platform.env" <<ENV
DB_SERVER=$(tf -raw sql_server_fqdn)
DB_NAME=$(field database_name)
SERVICEBUS_NAMESPACE=$(tf -raw servicebus_namespace).servicebus.windows.net
SERVICEBUS_QUEUE=$(field queue)
KEY_VAULT_URI=https://$(field key_vault_name).vault.azure.net/
ENV
cat > "${overlay}/deploy.env" <<ENV
IDENTITY_CLIENT_ID=$(field identity_client_id)
BACKEND_IMAGE=${registry}/${app}-backend:${tag}
WEB_IMAGE=${registry}/${app}-web:${tag}
ENV

echo "== Applying ${overlay} to namespace ${namespace}"
# A Job can't be changed once created, so remove the previous run before applying the new one.
kubectl delete job "${app}-migrate" -n "${namespace}" --ignore-not-found
kubectl apply -k "${overlay}"

echo "== Waiting for the database migration"
# 9 minutes: shorter than the Job's 10-minute deadline, so its pod still exists when we collect evidence below
# (at the deadline Kubernetes deletes the pod, and its logs and events go with it).
if ! kubectl wait --for=condition=complete "job/${app}-migrate" -n "${namespace}" --timeout=9m; then
  # Show WHY: the newest migration pod's status, its events (e.g. Pending: Insufficient cpu) and last log lines.
  newest="$(kubectl get pods -n "${namespace}" -l "app.kubernetes.io/name=${app}-migrate" \
    --sort-by=.metadata.creationTimestamp -o name | tail -1)"
  if [[ -z "${newest}" ]]; then
    echo "== Migration failed and no migration pod is left to inspect."
  else
    echo "== Migration failed. Status, events and last log lines of ${newest}:"
    kubectl get -n "${namespace}" "${newest}" -o wide || true
    kubectl describe -n "${namespace}" "${newest}" | sed -n '/^Events:/,$p' || true
    kubectl logs -n "${namespace}" "${newest}" --tail=20 || true
  fi
  kubectl describe job "${app}-migrate" -n "${namespace}" | sed -n '/^Events:/,$p'
  exit 1
fi

echo "== Waiting for each Deployment to become ready"
for deployment in $(kubectl get deployments -n "${namespace}" -o name); do
  kubectl rollout status "${deployment}" -n "${namespace}" --timeout=5m
done
kubectl get pods -n "${namespace}"
