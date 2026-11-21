"""Database tables ("the drawers in the filing cabinet").

Money is ALWAYS a whole number of cents (BIGINT): 25000 = $250.00. Never floating point.
The most important protections are database rules, not Python code:
  - accounts.balance_cents can never go below zero                       (CHECK)
  - one payment per (sender account, idempotency key)                     (UNIQUE) -> stops double-click debits
  - at most one debit and one credit ledger entry per payment             (UNIQUE) -> stops duplicate-message credits
Keep this file in sync with the migrations in migrations/versions/.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

UTC_NOW = text("SYSUTCDATETIME()")


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class PaymentStatus(enum.StrEnum):
    PENDING = "pending"  # accepted: sender debited, recipient not yet credited
    PROCESSING = "processing"  # a worker is crediting the recipient right now
    COMPLETED = "completed"  # recipient credited
    FAILED = "failed"  # could not be completed (and the sender is refunded)


class EntryType(enum.StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Unicode(254), unique=True)
    full_name: Mapped[str] = mapped_column(Unicode(200))
    password_hash: Mapped[str] = mapped_column(Unicode(255))  # the hash only, never the password
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("balance_cents >= 0", name="balance_non_negative"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    account_number: Mapped[str] = mapped_column(Unicode(12), unique=True)
    currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'CAD'"))
    # Opening balance is kept separately so we can reconcile:
    #   opening + credits - debits (from ledger_entries) == balance_cents
    opening_balance_cents: Mapped[int] = mapped_column(BigInteger)
    balance_cents: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint("from_account_id <> to_account_id", name="different_accounts"),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="status_valid"),
        # Guard #1: a double-clicked "Send" carries the same key, so the second insert is refused.
        UniqueConstraint("from_account_id", "idempotency_key", name="uq_payments_sender_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    from_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    to_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'CAD'"))
    status: Mapped[str] = mapped_column(Unicode(20), index=True, default=PaymentStatus.PENDING)
    idempotency_key: Mapped[str] = mapped_column(Unicode(64))
    correlation_id: Mapped[str] = mapped_column(Unicode(64))  # follows the payment API -> queue -> worker
    failure_reason: Mapped[str | None] = mapped_column(Unicode(500))
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)
    updated_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)
    completed_at: Mapped[datetime | None] = mapped_column(DATETIME2)


class LedgerEntry(Base):
    """Every movement of money. Append-only: rows are never updated or deleted."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint("entry_type IN ('debit', 'credit')", name="entry_type_valid"),
        # Guard #2: a duplicate Service Bus message can't create a second credit for the same payment.
        UniqueConstraint("payment_id", "entry_type", name="uq_ledger_entries_payment_entry_type"),
        Index("ix_ledger_entries_account_created", "account_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    entry_type: Mapped[str] = mapped_column(Unicode(6))
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)


class OutboxMessage(Base):
    """Messages waiting to be published to Service Bus. Written in the SAME transaction as the debit."""

    __tablename__ = "outbox_messages"
    __table_args__ = (Index("ix_outbox_messages_unpublished", "published_at", "created_at"),)

    # Also used as the Service Bus message ID, so a message can be traced back to its outbox row.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), index=True)
    message_type: Mapped[str] = mapped_column(Unicode(50))
    payload: Mapped[str] = mapped_column(UnicodeText)  # JSON
    correlation_id: Mapped[str] = mapped_column(Unicode(64))
    created_at: Mapped[datetime] = mapped_column(DATETIME2, server_default=UTC_NOW)
    published_at: Mapped[datetime | None] = mapped_column(DATETIME2)  # NULL = not yet sent
    publish_attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Unicode(500))
