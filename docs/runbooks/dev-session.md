# Runbook: start and end a dev session

Dev is rebuilt at the start of each working session and destroyed at the end, to stay within budget (ADR-0001).
Everything runs from `infrastructure/environments/dev`. Review every plan before applying it.

## Start (about 20 minutes, mostly waiting for AKS)
```bash
cd infrastructure/environments/dev
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform init -upgrade -backend-config=backend.hcl

# 1. Build the platform with your IP allowed, so the setup jobs can reach SQL and Key Vault (ADR-0010)
export TF_VAR_operator_ip="$(curl -s https://api.ipify.org)"
terraform plan -out tfplan         # review: a fresh environment is all "to add"
terraform apply tfplan

# 2. Connect kubectl (Entra ID sign-in)
az aks get-credentials -g rg-northstar-dev -n aks-northstar-dev --overwrite-existing
kubelogin convert-kubeconfig -l azurecli

# 3. Workload setup for each slice: namespace, database user, JWT signing key (safe to re-run)
../../scripts/workload-setup.sh payments dev
../../scripts/workload-setup.sh payments staging

# 4. Deploy: normally the pipeline does this on every merge to main (re-run its latest run in GitHub).
#    By hand: build both images in ACR from the merged commit, then deploy.
cd ../../..
TAG=$(git rev-parse HEAD)
ACR=$(terraform -chdir=infrastructure/environments/dev output -raw acr_login_server | cut -d. -f1)
az acr build -r "$ACR" -t "payments-backend:$TAG" --platform linux/amd64 apps/payments/backend
az acr build -r "$ACR" -t "payments-web:$TAG" --platform linux/amd64 apps/payments/web
infrastructure/scripts/deploy-workload.sh payments dev "$TAG"

# 5. Load 20 demo customers into payments-dev (after the migration has created the tables)
(cd apps/payments/backend && DB_AUTH=entra DB_NAME=payments DB_TRUST_SERVER_CERTIFICATE=false \
  DB_SERVER=$(terraform -chdir=../../../infrastructure/environments/dev output -raw sql_server_fqdn) \
  uv run python -m northstar_payments.seed --customers 20)
cd infrastructure/environments/dev

# 6. Close the public door again: SQL and Key Vault back to private-endpoint only
unset TF_VAR_operator_ip
terraform plan -out tfplan         # review: firewall rule destroyed, public access true -> false
terraform apply tfplan

# 7. Open the web page: http://localhost:8080
kubectl port-forward -n payments-dev svc/payments-web 8080:8080
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
| Free-offer database creation fails for the second database | The subscription's free-database limit; ask before switching staging to a paid serverless database |
| `sqlcmd: Unknown Option '-authentication-method'` | The older sqlcmd ran; install go-sqlcmd with `brew install sqlcmd` |
| `az acr build`: "the --mount option requires BuildKit" | ACR Tasks uses the classic builder; keep Dockerfiles free of BuildKit-only features |
| Migration Job `Error`, log says `Login timeout expired (HYT00)` | The serverless database was waking up; the Job retries by itself |
| Migration log says `FA005 Cannot use Access Token with ... Integrated Security` | `Trusted_Connection=Yes` wasn't removed before using the token (fixed in `common/db.py`) |
| `exec format error` in a pod | The image was built for the wrong chip (ARM on a Mac); build with `--platform linux/amd64` |
