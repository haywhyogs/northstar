# Runbook: start and end a dev session

Dev is rebuilt at the start of each working session and destroyed at the end, to stay within budget (ADR-0001).
Everything runs from `infrastructure/environments/dev`. Review every plan before applying it.

## Start (about 15 minutes, mostly waiting for AKS)
```bash
cd infrastructure/environments/dev
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform init -upgrade -backend-config=backend.hcl

# 1. Build the platform with your IP allowed, so the setup jobs can reach SQL and Key Vault (ADR-0010)
export TF_VAR_operator_ip="$(curl -s https://api.ipify.org)"
terraform plan -out tfplan         # review: a fresh environment is all "to add"
terraform apply tfplan

# 2. Workload setup jobs: database user + JWT signing key (safe to re-run)
../../scripts/workload-setup.sh payments

# 3. Close the public door again: SQL and Key Vault back to private-endpoint only
unset TF_VAR_operator_ip
terraform plan -out tfplan         # review: firewall rule destroyed, public access true -> false
terraform apply tfplan

# 4. Connect kubectl (Entra ID sign-in)
az aks get-credentials -g rg-northstar-dev -n aks-northstar-dev --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
kubectl get nodes
```

## End (every session, no exceptions)
```bash
cd infrastructure/environments/dev
terraform plan -destroy -out destroy.tfplan   # review: everything "to destroy", nothing else
terraform apply destroy.tfplan
```
The state storage (bootstrap) is never destroyed.

## If it breaks
| Symptom | Likely cause |
|---|---|
| `VM size ... is not allowed in your subscription` | Pick a size from the list in the error; set `vm_size` in the environment |
| SQL error 40613 "not currently available" | The serverless database is waking up; the script retries |
| `Client address is not authorized` / `is not allowed to access the server` | Your IP changed: export `TF_VAR_operator_ip` again, plan, apply |
| `Forbidden` from Key Vault right after apply | New role assignments take a few minutes to take effect; retry |
| `sqlcmd: Unknown Option '-authentication-method'` | The older sqlcmd ran; install go-sqlcmd with `brew install sqlcmd` |
