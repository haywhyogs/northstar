# database module: changelog

## v1.1.0
- Optional private endpoint (`private_endpoint`), registered in the private DNS zone.
- Optional `operator_ip`: opens the public endpoint to that single IP for setup tasks. Unset = fully private.
  Backwards compatible: callers need no changes (MINOR release).

## v1.0.0
- Azure SQL logical server, Entra ID only, public network access disabled.
