"""Configuration, read from environment variables (and a local .env file when present).

The same code runs everywhere; only the environment variables change:
  - Your Mac:   values come from apps/payments/.env (git-ignored)
  - Kubernetes: values come from a ConfigMap, and there is NO password at all (Entra ID auth via AKS workload identity)
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # "../.env" = apps/payments/.env when commands are run from apps/payments/backend.
    # Missing files are simply ignored (e.g. inside containers).
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "northstar"

    # "sql"   = username + password (local development only)
    # "entra" = passwordless Microsoft Entra ID token via workload identity (Azure)
    db_auth: Literal["sql", "entra"] = "sql"
    db_user: str = "sa"
    # Reuses the local SQL Server password from .env. SecretStr stops it being printed in logs by accident.
    db_password: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DB_PASSWORD", "MSSQL_SA_PASSWORD")
    )

    # Driver 18 encrypts connections by default and checks the server's certificate.
    # Locally, SQL Server uses a self-signed certificate, so we trust it explicitly. NEVER true in Azure.
    db_trust_server_certificate: bool = False

    # Local demo only: the shared login password for seeded synthetic customers (stored hashed).
    demo_customer_password: SecretStr | None = None

    # Customer login tokens (ADR-0007). Locally from .env; in Azure from Key Vault via workload identity.
    jwt_signing_key: SecretStr | None = None
    # Azure only: e.g. https://kv-payments-dev-xxxxx.vault.azure.net/ . The key is read from secret "jwt-signing-key".
    key_vault_uri: str | None = None
    jwt_ttl_minutes: int = 15

    log_level: str = "INFO"

    # Service Bus. Locally: the emulator's documented connection string (not a secret).
    # In Azure: no connection string; the workload identity is used instead (added with the AKS platform).
    servicebus_connection_string: SecretStr | None = None
    # Azure only: e.g. sb-northstar-dev-xxxxx.servicebus.windows.net (used when there is no connection string)
    servicebus_namespace: str | None = None
    servicebus_queue: str = "payments"
    dispatcher_batch_size: int = 20
    dispatcher_idle_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
