"""Database connection: builds the SQLAlchemy engine from Settings."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL

from northstar_payments.common.config import Settings, get_settings

ODBC_DRIVER = "ODBC Driver 18 for SQL Server"


def build_url(settings: Settings) -> URL:
    query = {
        "driver": ODBC_DRIVER,
        "Encrypt": "yes",
        "TrustServerCertificate": "yes" if settings.db_trust_server_certificate else "no",
    }
    if settings.db_auth == "sql":
        if settings.db_password is None:
            raise RuntimeError("DB_PASSWORD (or MSSQL_SA_PASSWORD) is not set. Check apps/payments/.env")
        # URL.create escapes special characters, and SQLAlchemy masks the password if the URL is ever printed.
        return URL.create(
            "mssql+pyodbc",
            username=settings.db_user,
            password=settings.db_password.get_secret_value(),
            host=settings.db_server,
            port=settings.db_port,
            database=settings.db_name,
            query=query,
        )
    # Passwordless Entra ID authentication (AKS workload identity) is added with the AKS platform.
    raise NotImplementedError("db_auth='entra' is not implemented yet (AKS workload identity)")


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping: test a pooled connection before using it, so a database restart doesn't break requests.
    return create_engine(build_url(get_settings()), pool_pre_ping=True)
