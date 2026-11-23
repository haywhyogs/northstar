"""The Azure (passwordless) settings: no secrets in the connection details."""

import struct

from northstar_payments.common.config import Settings
from northstar_payments.common.db import build_url


def test_entra_database_url_has_no_username_or_password():
    # _env_file=None: ignore your local .env (it trusts the local SQL Server's self-signed certificate).
    settings = Settings(
        _env_file=None, db_auth="entra", db_server="sql-x.database.windows.net", db_name="payments"
    )
    url = build_url(settings)
    assert url.username is None
    assert url.password is None
    assert url.query["Encrypt"] == "yes"
    assert url.query["TrustServerCertificate"] == "no"


def test_sql_token_is_packed_for_the_odbc_driver(monkeypatch):
    from northstar_payments.common import azure

    class FakeCredential:
        def get_token(self, scope):
            assert scope == "https://database.windows.net/.default"
            return type("Token", (), {"token": "abc"})()

    monkeypatch.setattr(azure, "get_credential", lambda: FakeCredential())
    packed = azure.sql_access_token()
    (length,) = struct.unpack("<I", packed[:4])
    assert length == len("abc".encode("utf-16-le"))
    assert packed[4:].decode("utf-16-le") == "abc"
