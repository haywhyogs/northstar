"""Passwordless access to Azure services (ADR-0010).

In AKS, workload identity puts three environment variables into the pod (AZURE_CLIENT_ID, AZURE_TENANT_ID,
AZURE_FEDERATED_TOKEN_FILE). DefaultAzureCredential reads them and swaps the pod's Kubernetes token for an
Entra ID token. On a laptop, the same code uses your `az login` instead. No secret is ever stored.
"""

import struct
from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Scope = "which service is this token for". Azure SQL always uses this one.
SQL_TOKEN_SCOPE = "https://database.windows.net/.default"


@lru_cache
def get_credential() -> DefaultAzureCredential:
    # One shared credential: it caches tokens and refreshes them before they expire.
    return DefaultAzureCredential()


def sql_access_token() -> bytes:
    """An Entra ID token for Azure SQL, packed the way the ODBC driver expects (length + UTF-16 text)."""
    token = get_credential().get_token(SQL_TOKEN_SCOPE).token.encode("utf-16-le")
    return struct.pack(f"<I{len(token)}s", len(token), token)


@lru_cache
def get_secret(vault_uri: str, name: str) -> str:
    """Read a secret from Key Vault once and keep it in memory. Restart the pods to pick up a new value."""
    return SecretClient(vault_url=vault_uri, credential=get_credential()).get_secret(name).value or ""
