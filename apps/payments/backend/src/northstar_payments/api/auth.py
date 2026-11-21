"""Customer login and token verification (ADR-0007)."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from northstar_payments.api.deps import get_session
from northstar_payments.api.schemas import LoginRequest, TokenResponse
from northstar_payments.common.config import Settings, get_settings
from northstar_payments.common.models import Customer
from northstar_payments.common.security import hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

ISSUER = "northstar-payments"
ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)
# Checked when the email doesn't exist, so a failed login takes the same time either way
# (an attacker can't tell which emails are registered by timing the response).
_DUMMY_HASH = hash_password(uuid.uuid4().hex)


def _signing_key(settings: Settings) -> str:
    if settings.jwt_signing_key is None:
        raise RuntimeError("JWT_SIGNING_KEY is not set. Check apps/payments/.env")
    key = settings.jwt_signing_key.get_secret_value()
    if len(key) < 32:
        raise RuntimeError("JWT_SIGNING_KEY must be at least 32 characters")
    return key


def create_access_token(customer_id: uuid.UUID, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    ttl_seconds = settings.jwt_ttl_minutes * 60
    claims = {"sub": str(customer_id), "iss": ISSUER, "iat": now, "exp": now + timedelta(seconds=ttl_seconds)}
    return jwt.encode(claims, _signing_key(settings), algorithm=ALGORITHM), ttl_seconds


def current_customer_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> uuid.UUID:
    """Dependency for protected endpoints: a valid, unexpired token signed by us, or 401."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = jwt.decode(
            credentials.credentials,
            _signing_key(settings),
            algorithms=[ALGORITHM],  # pinned: never accept a token that names its own algorithm
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        return uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized from None


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    customer = session.scalar(select(Customer).where(Customer.email == body.email.strip().lower()))
    password_ok = verify_password(
        body.password.get_secret_value(), customer.password_hash if customer else _DUMMY_HASH
    )
    if customer is None or not password_ok:
        logger.info("login failed")  # no email in logs: it's personal data
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token, ttl_seconds = create_access_token(customer.id, settings)
    logger.info("login succeeded", extra={"fields": {"customer_id": str(customer.id)}})
    return TokenResponse(access_token=token, expires_in=ttl_seconds)
