"""Shared FastAPI dependencies."""

from collections.abc import Iterator

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from northstar_payments.common.db import get_engine
from northstar_payments.common.models import Account


def get_session() -> Iterator[Session]:
    """One database session per request. Anything not committed is rolled back when the request ends."""
    with Session(get_engine()) as session:
        yield session


def get_own_account(session: Session, customer_id) -> Account:
    """The logged-in customer's account. Customers can only ever act on their OWN account."""
    account = session.scalar(select(Account).where(Account.customer_id == customer_id))
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return account


def format_cents(cents: int) -> str:
    """1234567 -> '12345.67' using whole-number maths (no floating-point rounding)."""
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(cents), 100)
    return f"{sign}{whole}.{part:02d}"
