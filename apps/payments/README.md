# Payments workload (Payments team)

The demo banking workload running on the Northstar platform: web frontend, Python API, outbox dispatcher and payment worker.

## Run the backing services locally
```bash
cd apps/payments
cp .env.example .env          # then edit .env: accept the licences, set a local password
docker compose config --quiet # validate the file (no output = OK)
docker compose up -d          # start SQL Server, create the database, start the Service Bus emulator
docker compose ps             # sqlserver = healthy, servicebus = running, db-init = exited (0)
curl http://localhost:5300/health
```
Stop with `docker compose down`. Add `-v` to also delete the local database files.

| Local service | Stands in for (Azure) | Address from your Mac |
|---|---|---|
| `sqlserver` | Azure SQL Database | `localhost,1433` · database `northstar` |
| `servicebus` | Azure Service Bus | `sb://localhost` (AMQP 5672) · queue `payments` |

## Database migrations (from `apps/payments/backend/`)
```bash
uv sync                          # create .venv and install dependencies (pinned in uv.lock)
uv run alembic upgrade head --sql  # PREVIEW the SQL (connects to nothing, changes nothing)
uv run alembic upgrade head      # apply migrations not yet recorded in alembic_version
uv run alembic current           # which migration is the database on?
```

## Demo data (synthetic only)
Set `DEMO_CUSTOMER_PASSWORD` in `.env` first (only its hash is stored). Then, from `backend/`:
```bash
uv run python -m northstar_payments.seed --customers 300   # 300 customers, $1,000.00 each; safe to re-run
```

Emulator connection string (a public, documented placeholder, not a secret):
`Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;`
