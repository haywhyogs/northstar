"""Database connection: builds the SQLAlchemy engine from Settings."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL

from northstar_payments.common.config import Settings, get_settings

# ODBC option number for "here is an access token instead of a password" (defined by Microsoft's driver).
SQL_COPT_SS_ACCESS_TOKEN = 1256

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


def use_access_token(cargs: list, cparams: dict, token: bytes) -> None:
    """Hand the driver an Entra ID token instead of a password, for one new connection.

    With no username in the URL, SQLAlchemy adds "Trusted_Connection=Yes" (Windows sign-in). The ODBC driver
    refuses a token combined with that option (error FA005), so it is removed first.
    https://docs.sqlalchemy.org/en/20/dialects/mssql.html#connecting-to-databases-with-access-tokens
    """
    cargs[0] = cargs[0].replace(";Trusted_Connection=Yes", "")
    cparams["attrs_before"] = {SQL_COPT_SS_ACCESS_TOKEN: token}


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping: test a pooled connection before using it, so a database restart doesn't break requests.
    settings = get_settings()
    engine = create_engine(build_url(settings), pool_pre_ping=True)
    if settings.db_auth == "entra":
        from northstar_payments.common.azure import sql_access_token

        @event.listens_for(engine, "do_connect")
        def _provide_token(dialect, conn_rec, cargs, cparams):
            use_access_token(cargs, cparams, sql_access_token())

    return engine
