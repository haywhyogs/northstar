"""Database connection: builds the SQLAlchemy engine from Settings."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
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
    # Entra ID: no username or password in the URL. A token is handed to the driver on every new connection.
    return URL.create(
        "mssql+pyodbc", host=settings.db_server, port=settings.db_port, database=settings.db_name, query=query
    )


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping: test a pooled connection before using it, so a database restart doesn't break requests.
    settings = get_settings()
    engine = create_engine(build_url(settings), pool_pre_ping=True)
    if settings.db_auth == "entra":
        from northstar_payments.common.azure import SQL_COPT_SS_ACCESS_TOKEN, sql_access_token

        @event.listens_for(engine, "do_connect")
        def _provide_token(dialect, conn_rec, cargs, cparams):
            # Fresh (cached) token for each new connection, so expired tokens are never reused.
            cparams["attrs_before"] = {SQL_COPT_SS_ACCESS_TOKEN: sql_access_token()}

    return engine
