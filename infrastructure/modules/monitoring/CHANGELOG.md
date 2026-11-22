# monitoring module: changelog

## v1.1.0
- Added `local_authentication_enabled` (default `false`): the Log Analytics workspace accepts only Entra ID identities, no shared keys.
  Backwards compatible: callers need no changes (MINOR release).

## v1.0.0
- Log Analytics workspace (PerGB2018, retention, daily ingestion cap) and workspace-based Application Insights.
