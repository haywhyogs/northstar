# Architecture

> Living document. Diagrams use Mermaid, which GitHub renders automatically.

## 1. The four layers and the end-to-end journey

```mermaid
flowchart TB
  subgraph L1["1 · Developer workflow"]
    ENG["Platform/app engineer<br/>(main GitHub account)"] -->|feature branch| PR[Pull request]
    REV["Independent reviewer<br/>(second GitHub account)"] -->|approves| PR
  end

  subgraph L2["2 · Delivery platform: GitHub Actions"]
    CHK["Parallel checks<br/>tests · terraform plan · scans"] --> BLD["Build image once<br/>tag = commit SHA"]
    BLD --> PUSH[Push to ACR]
    PUSH --> DEV["Deploy to *-dev<br/>+ smoke tests"]
    DEV --> GATE{{"Manual approval<br/>(reviewer)"}}
    GATE --> STG["Deploy same image to *-staging<br/>+ smoke tests"]
  end

  subgraph L3["3 · Azure foundation"]
    OIDC["Entra ID<br/>OIDC federation"]
    AKS[AKS cluster]
    ACR[(Container Registry)]
  end

  subgraph L4["4 · Workloads and operations"]
    APP["payments: web · api · worker<br/>fx-rates: api"]
    MON["Azure Monitor · Log Analytics<br/>App Insights · alerts · workbook"]
  end

  PR --> CHK
  L2 -. "no stored secrets" .-> OIDC
  PUSH --> ACR
  STG --> AKS
  AKS --> APP
  APP --> MON
```

## 2. Azure foundation (budget version: ADR-0001, ADR-0004)

```mermaid
flowchart LR
  U[Browser] -->|HTTPS| ING[Ingress]
  subgraph RG["Resource group · rg-northstar-dev · Canada Central"]
    subgraph VNet["VNet"]
      subgraph AKSsub["AKS subnet"]
        subgraph AKS["AKS cluster (1 small node)"]
          ING
          subgraph NS1["ns: payments-dev / payments-staging"]
            WEB[web] --- API[api] --- DSP[dispatcher] --- WRK[worker]
          end
          subgraph NS2["ns: fx-rates-dev / fx-rates-staging"]
            FX[fx-rates api]
          end
        end
      end
      subgraph PEsub["Private endpoint subnet"]
        PESQL([SQL private endpoint])
        PEKV([Key Vault private endpoint])
      end
    end
    DNS["Private DNS zones<br/>privatelink.database.windows.net<br/>privatelink.vaultcore.azure.net"]
    SQL[(Azure SQL Database<br/>free offer)]
    KV[Key Vault]
    SB[["Service Bus (Basic)<br/>public endpoint · Entra-only"]]
    ACR[("ACR (Basic)<br/>public endpoint · Entra-only")]
    LAW[Log Analytics + App Insights]
  end
  PESQL --- SQL
  PEKV --- KV
  VNet -. resolves via .- DNS
  API --> PESQL
  WRK --> PESQL
  DSP --> SB --> WRK
  API -. workload identity .-> PEKV
  AKS -. AcrPull .-> ACR
  AKS -. logs/metrics .-> LAW
```

**Why SQL and Key Vault are private but Service Bus and ACR aren't:** private endpoints for Service Bus and ACR
need their Premium tiers (hundreds of USD per month). They stay on public endpoints that only accept Entra ID identities. See ADR-0001.

## 3. Three separate identities

| Identity | Who | How it authenticates | What it may do |
|---|---|---|---|
| CI/CD identity | GitHub Actions | OIDC federation (short-lived token, no stored secret) | Push to ACR, deploy to AKS, run Terraform |
| Workload identity | Pods (one per app) | AKS workload identity (federated with a Kubernetes service account) | Only that app's SQL database, queue and Key Vault secrets |
| Customer identity | Bank customers | App login (password hash in SQL, session token) | Only their own accounts and transactions |

A compromised pipeline can't read customer data. A compromised pod can't change infrastructure. A customer can't see another customer's account.

## 4. Payments data model

Money is stored as whole **cents** (`BIGINT`). Source: `apps/payments/backend/migrations/versions/`.

```mermaid
erDiagram
    customers ||--o{ accounts : owns
    accounts ||--o{ payments : "sends (from)"
    accounts ||--o{ payments : "receives (to)"
    payments ||--|{ ledger_entries : "records money movement"
    accounts ||--o{ ledger_entries : "is moved on"
    payments ||--o{ outbox_messages : "announces"

    customers { uuid id PK
      nvarchar email UK
      nvarchar password_hash }
    accounts { uuid id PK
      nvarchar account_number UK
      bigint opening_balance_cents
      bigint balance_cents "CHECK >= 0" }
    payments { uuid id PK
      bigint amount_cents "CHECK > 0"
      nvarchar status "pending|processing|completed|failed"
      nvarchar idempotency_key "UNIQUE per sender"
      nvarchar correlation_id }
    ledger_entries { bigint id PK
      nvarchar entry_type "debit|credit, UNIQUE per payment"
      bigint amount_cents }
    outbox_messages { uuid id PK
      nvarchar payload "JSON"
      datetime2 published_at "NULL = not sent yet" }
```

| Rule (enforced by the database) | Protects against |
|---|---|
| `ck_accounts_balance_non_negative` | Overdrafts, even if application code has a bug |
| `uq_payments_sender_idempotency_key` | **Double-click** creating two payments and two debits |
| `uq_ledger_entries_payment_entry_type` | **Duplicate Service Bus message** crediting twice |
| Reconciliation: `opening + credits − debits = balance` | Silent drift between the ledger and balances |

## 5. Payment flow (the reliability scenario)

```mermaid
sequenceDiagram
    autonumber
    actor A as Customer A
    participant API as API (teller)
    participant DB as Azure SQL (ledger)
    participant D as Dispatcher (mail runner)
    participant SB as Service Bus (post office)
    participant W as Worker (clerk)

    A->>API: Send $250 to Customer B
    API->>DB: ONE transaction: payment (pending) + debit A + outbox row
    API-->>A: "Payment pending"
    D->>DB: Read unsent outbox rows
    D->>SB: Publish message (payment id, correlation id)
    D->>DB: Mark outbox row sent
    SB->>W: Deliver (may happen more than once!)
    W->>DB: ONE transaction: already processed? skip. Otherwise credit B + mark completed
    W->>SB: Complete message
    Note over SB,W: Worker down → messages wait in the queue, payment stays pending.<br/>Repeated failures → dead-letter queue.
```
