# networking module: changelog

## v1.1.0
- Private DNS zones for Azure SQL and Key Vault, linked to the VNet. Output `private_dns_zone_ids`.
  Backwards compatible: callers need no changes (MINOR release).

## v1.0.0
- VNet with an AKS subnet and a private endpoint subnet, each with its own NSG.
