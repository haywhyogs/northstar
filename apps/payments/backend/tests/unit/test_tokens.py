"""Login tokens (ADR-0007): accepted only when signed by us, unexpired and from our issuer."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from northstar_payments.api.auth import ALGORITHM, ISSUER, create_access_token, current_customer_id
from northstar_payments.common.config import Settings

KEY = "k" * 40  # throwaway test key, not a real secret
SETTINGS = Settings(jwt_signing_key=KEY, jwt_ttl_minutes=15)


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_identifies_the_customer() -> None:
    customer_id = uuid.uuid4()
    token, ttl = create_access_token(customer_id, SETTINGS)
    assert ttl == 15 * 60
    assert current_customer_id(bearer(token), SETTINGS) == customer_id


def test_missing_token_is_401() -> None:
    with pytest.raises(HTTPException) as caught:
        current_customer_id(None, SETTINGS)
    assert caught.value.status_code == 401


def test_token_signed_with_another_key_is_rejected() -> None:
    token, _ = create_access_token(uuid.uuid4(), Settings(jwt_signing_key="x" * 40))
    with pytest.raises(HTTPException) as caught:
        current_customer_id(bearer(token), SETTINGS)
    assert caught.value.status_code == 401


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    claims = {"sub": str(uuid.uuid4()), "iss": ISSUER, "iat": past, "exp": past + timedelta(minutes=15)}
    token = jwt.encode(claims, KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as caught:
        current_customer_id(bearer(token), SETTINGS)
    assert caught.value.status_code == 401


def test_unsigned_token_is_rejected() -> None:
    claims = {"sub": str(uuid.uuid4()), "iss": ISSUER, "iat": 0, "exp": 9999999999}
    token = jwt.encode(claims, None, algorithm="none")  # the classic "alg: none" attack
    with pytest.raises(HTTPException):
        current_customer_id(bearer(token), SETTINGS)


def test_short_signing_key_is_refused() -> None:
    with pytest.raises(RuntimeError):
        create_access_token(uuid.uuid4(), Settings(jwt_signing_key="too-short"))
