#!/usr/bin/env bash
# Smoke test: one real request through the whole chain, from INSIDE the namespace:
#   web (nginx) -> payments-api -> database (private endpoint, workload identity).
#   infrastructure/scripts/smoke-test.sh payments dev
# Passes only if /api/health/ready answers 200. Runs a short-lived curl pod that meets the "restricted" policy.
set -euo pipefail

app="${1:?usage: smoke-test.sh <app> <env>}"
env="${2:?usage: smoke-test.sh <app> <env>}"
namespace="${app}-${env}"
url="http://${app}-web:8080/api/health/ready"

overrides='{
  "spec": {
    "securityContext": {"runAsNonRoot": true, "runAsUser": 100, "seccompProfile": {"type": "RuntimeDefault"}},
    "containers": [{
      "name": "smoke",
      "image": "curlimages/curl:8.11.1",
      "args": ["-fsS", "--retry", "10", "--retry-delay", "3", "--retry-all-errors", "'"${url}"'"],
      "securityContext": {"allowPrivilegeEscalation": false, "capabilities": {"drop": ["ALL"]}}
    }]
  }
}'

echo "== Smoke test: GET ${url} (namespace ${namespace})"
kubectl run "smoke-$(date +%s)" -n "${namespace}" --rm -i --restart=Never \
  --image=curlimages/curl:8.11.1 --overrides="${overrides}"
echo
echo "== Smoke test passed"
