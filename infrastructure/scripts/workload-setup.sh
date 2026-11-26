#!/usr/bin/env bash
# One-off setup for a workload slice after `terraform apply` (ADR-0010). Safe to run again: it skips what's done.
#   1. Creates the Kubernetes namespace (the platform owns namespaces; the pipeline can't create them).
#   2. Adds the slice's identity to its database's user list (CREATE USER ... FROM EXTERNAL PROVIDER).
#   3. Stores a random JWT signing key in the slice's Key Vault, if none exists yet.
#
# Run from anywhere (it finds the platform folder itself), while operator_ip is set and kubectl is connected:
#   ~/Desktop/Northstar/infrastructure/scripts/workload-setup.sh payments dev
#   ~/Desktop/Northstar/infrastructure/scripts/workload-setup.sh payments staging
# PLATFORM picks the Terraform folder to read (default dev), like deploy-workload.sh.
# Needs: az (logged in as the SQL Entra admin), terraform, jq, kubectl, openssl, go-sqlcmd (`brew install sqlcmd`).
# Secrets are never printed or written to disk.
set -euo pipefail

app="${1:?usage: workload-setup.sh <app> <env>   e.g. payments dev}"
env="${2:?usage: workload-setup.sh <app> <env>   e.g. payments dev}"
namespace="${app}-${env}"

# Read Terraform outputs from the platform folder, wherever this script is called from.
cd "$(dirname "$0")/../environments/${PLATFORM:-dev}"

# go-sqlcmd (supports Entra sign-in). The older mssql-tools18 sqlcmd may come first on PATH, so use Homebrew's path.
sqlcmd="$(brew --prefix sqlcmd 2>/dev/null)/bin/sqlcmd"
[[ -x "$sqlcmd" ]] || { echo "go-sqlcmd not found: run 'brew install sqlcmd'"; exit 1; }

workload="$(terraform output -json workloads | jq -e --arg ns "$namespace" '.[$ns]')" \
  || { echo "No workload '${namespace}' in this platform's outputs"; exit 1; }
field() { jq -r --arg f "$1" '.[$f]' <<<"$workload"; }
server="$(terraform output -raw sql_server_fqdn)"
database="$(field database_name)"
identity="$(field identity_name)"
vault="$(field key_vault_name)"

echo "== 1/3 Namespace ${namespace}"
# "restricted": Kubernetes refuses pods that run as root or skip the security settings.
kubectl apply -f - <<YAML
apiVersion: v1
kind: Namespace
metadata:
  name: ${namespace}
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
YAML

run_sql() {
  # -b: exit with an error code if any SQL statement fails (otherwise sqlcmd prints the error and "succeeds").
  "$sqlcmd" -S "$server" -d "$database" --authentication-method ActiveDirectoryDefault -b -h -1 -W -Q "$1"
}

echo "== 2/3 Database access for ${identity} on ${database}"
# Serverless databases pause when idle; the first connection wakes them (error 40613 for about a minute).
for attempt in 1 2 3 4 5 6; do
  if exists="$(run_sql "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.database_principals WHERE name = '${identity}'" 2>&1)"; then
    break
  fi
  if [[ "$exists" == *40613* && $attempt -lt 6 ]]; then
    echo "   database is waking up, retrying in 20 s (attempt ${attempt}/6)"
    sleep 20
  else
    echo "$exists"
    echo "   Can't connect. Is operator_ip set and applied, and is your IP unchanged?"
    exit 1
  fi
done

if [[ "$(echo "$exists" | tr -d '[:space:]')" == "1" ]]; then
  echo "   already granted, skipping"
else
  # WITH OBJECT_ID: tell SQL exactly which Entra identity this is, instead of SQL looking the name up in Entra ID.
  # The name lookup depends on SQL reaching Microsoft Graph on your behalf, and can fail for brand-new identities.
  object_id="$(az identity show -g "$(terraform output -raw resource_group_name)" -n "$identity" --query principalId -o tsv)"
  run_sql "CREATE USER [${identity}] FROM EXTERNAL PROVIDER WITH OBJECT_ID = '${object_id}';
           ALTER ROLE db_datareader ADD MEMBER [${identity}];
           ALTER ROLE db_datawriter ADD MEMBER [${identity}];
           ALTER ROLE db_ddladmin ADD MEMBER [${identity}];"
  echo "   granted"
fi

echo "== 3/3 JWT signing key in ${vault}"
if az keyvault secret show --vault-name "$vault" --name jwt-signing-key --query name -o tsv >/dev/null 2>&1; then
  echo "   already stored, skipping"
else
  az keyvault secret set --vault-name "$vault" --name jwt-signing-key \
    --value "$(openssl rand -base64 48)" --output none
  echo "   stored"
fi

echo "Done: ${namespace}."
