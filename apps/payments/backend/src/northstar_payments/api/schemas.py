"""Request and response shapes (validated automatically by FastAPI/Pydantic)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SecretStr

# Business limit: $10,000.00 per payment, checked before touching the database.
MAX_PAYMENT_CENTS = 1_000_000


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)  # SecretStr: never printed in logs or errors


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds


class AccountResponse(BaseModel):
    account_number: str
    currency: str
    balance_cents: int
    balance: str  # e.g. "1000.00", for display


class TransactionItem(BaseModel):
    payment_id: uuid.UUID
    direction: Literal["debit", "credit"]
    amount_cents: int
    amount: str
    counterparty_account_number: str
    payment_status: str
    created_at: datetime


class PaymentRequest(BaseModel):
    to_account_number: str = Field(min_length=1, max_length=12)
    amount_cents: int = Field(gt=0, le=MAX_PAYMENT_CENTS)


class PaymentResponse(BaseModel):
    payment_id: uuid.UUID
    status: str
    amount_cents: int
    amount: str
    currency: str
    from_account_number: str
    to_account_number: str
    correlation_id: str
    created_at: datetime
    completed_at: datetime | None
