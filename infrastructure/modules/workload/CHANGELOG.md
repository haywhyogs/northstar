# workload module: changelog

## v1.1.0
- Added `database_name` (default: the app name), so two environments of one app (payments-dev, payments-staging) can
  share one SQL server. Backwards compatible: callers need no changes (MINOR release).

## v1.0.0
- Per-workload, per-environment resources: user-assigned identity with a federated credential for the AKS
  service account, a free-offer Azure SQL database (azapi), Service Bus queues with send/receive roles,
  and a Key Vault (RBAC, private endpoint, optional operator IP).
