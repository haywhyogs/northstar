#!/usr/bin/env bash
# One-off setup for a workload after `terraform apply` (ADR-0010). Safe to run again: it skips what's already done.
#   1. Adds the workload's identity to its database's user list (CREATE USER ... FROM EXTERNAL PROVIDER).
#   2. Stores a random JWT signing key in the workload's Key Vault, if none exists yet.
#
# Run it from an environment folder (e.g. infrastructure/environments/dev), while operator_ip is set:
#   ../../scripts/workload-setup.sh payments
# Needs: az (logged in as the SQL Entra admin), terraform, openssl, and go-sqlcmd (`brew install sqlcmd`).
# Secrets are never printed or written to disk.
set -euo pipefail

app="${1:?usage: workload-setup.sh <app>   e.g. payments}"
prefix="${app//-/_}" # Terraform output names use underscores: fx-rates -> fx_rates

# go-sqlcmd (supports Entra sign-in). The older mssql-tools18 sqlcmd may come first on PATH, so use Homebrew's path.
sqlcmd="$(brew --prefix sqlcmd 2>/dev/null)/bin/sqlcmd"
[[ -x "$sqlcmd" ]] || { echo "go-sqlcmd not found: run 'brew install sqlcmd'"; exit 1; }

server="$(terraform output -raw sql_server_fqdn)"
grant_sql="$(terraform output -raw "${prefix}_database_grant_sql")"
vault="$(terraform output -raw "${prefix}_key_vault_name")"
database="$app"
identity="id-${app}-$(basename "$PWD")"

run_sql() {
  "$sqlcmd" -S "$server" -d "$database" --authentication-method ActiveDirectoryDefault -h -1 -W -Q "$1"
}

echo "== 1/2 Database access for ${identity} on ${database}"
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
  run_sql "$grant_sql"
  echo "   granted"
fi

echo "== 2/2 JWT signing key in ${vault}"
if az keyvault secret show --vault-name "$vault" --name jwt-signing-key --query name -o tsv >/dev/null 2>&1; then
  echo "   already stored, skipping"
else
  az keyvault secret set --vault-name "$vault" --name jwt-signing-key \
    --value "$(openssl rand -base64 48)" --output none
  echo "   stored"
fi

echo "Done. Now unset TF_VAR_operator_ip, then plan and apply to make SQL and Key Vault private again."
