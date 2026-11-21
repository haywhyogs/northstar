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

## Run the API locally (from `backend/`)
```bash
uv run uvicorn northstar_payments.api.main:app --port 8000 --no-access-log
```
Developer test page (not for customers): http://127.0.0.1:8000/docs

| Endpoint | Purpose |
|---|---|
| `POST /auth/login` | Email + password → 15-minute bearer token (ADR-0007) |
| `GET /accounts/me` | Own balance |
| `GET /accounts/me/transactions` | Own ledger history, newest first |
| `POST /payments` | Send money. Requires an `Idempotency-Key` header; repeating it returns the original payment (200) instead of paying twice |
| `GET /payments/{id}` | Status of a payment you sent or received |
| `GET /health/live`, `/health/ready` | Liveness (process up) and readiness (database reachable) |

Every response carries an `X-Correlation-ID` header, and every log line is JSON with the same `correlation_id`.

## Run the dispatcher and worker (from `backend/`, one terminal each)
```bash
uv run python -m northstar_payments.dispatcher   # outbox -> Service Bus
uv run python -m northstar_payments.worker       # Service Bus -> credit recipient, mark completed
```
Stop either with Ctrl+C (it finishes the current message first). Same image as the API, different start command (ADR-0003).

## Tests (from `backend/`)
```bash
uv run pytest -m "not integration"   # unit tests: no database, under a second
uv run pytest -m integration         # integration tests: needs the local stack + migrations
uv run pytest                        # everything
```
Integration tests create their own throwaway customers (`test-…@northstar.test`, accounts `T…`) and never touch the demo data.
They prove: debit + outbox in one transaction, double-click charges once, overdrafts change nothing,
a duplicate message credits once, and the ledger reconciles with balances.

## Run the customer web page locally (from `web/`)
With the API running in another terminal:
```bash
npm install     # first time only (versions pinned in package-lock.json)
npm run dev     # http://localhost:5173
```
One page: sign in, balance, send money, recent activity. Pending payments refresh every 5 seconds.
The page calls `/api/...`, which is forwarded to the API on port 8000 (Vite locally, nginx in Kubernetes).

## Run everything in containers (our 2 images)
```bash
docker compose --profile app up -d --build   # builds backend + web images, migrates, starts all
docker compose --profile app ps              # migrate = exited (0), api = healthy, others running
```
Open http://localhost:8080. Stop with `docker compose --profile app down`.

| Image | Containers | Notes |
|---|---|---|
| `northstar-payments-backend` | `migrate` (one-off), `api`, `dispatcher`, `worker` | Multi-stage, non-root (uid 10001), ODBC Driver 18 |
| `northstar-payments-web` | `web` | Static files on nginx (non-root, port 8080); forwards `/api/` to `api:8000` |
