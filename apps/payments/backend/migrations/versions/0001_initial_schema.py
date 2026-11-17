"""Renovation #1: initial schema (customers, accounts, payments, ledger_entries, outbox_messages)

Revision ID: 0001
Revises:
Create Date: 2026-11-16

Written by hand (not auto-generated) so every rule is visible and reviewable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mssql import DATETIME2

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_NOW = sa.text("SYSUTCDATETIME()")


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Unicode(254), nullable=False),
        sa.Column("full_name", sa.Unicode(200), nullable=False),
        sa.Column("password_hash", sa.Unicode(255), nullable=False),
        sa.Column("created_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.UniqueConstraint("email", name="uq_customers_email"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("account_number", sa.Unicode(12), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'CAD'"), nullable=False),
        sa.Column("opening_balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("created_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_accounts_customer_id_customers"),
        sa.UniqueConstraint("account_number", name="uq_accounts_account_number"),
        # The database itself refuses any change that would make a balance negative.
        sa.CheckConstraint("balance_cents >= 0", name=op.f("ck_accounts_balance_non_negative")),
    )
    op.create_index("ix_accounts_customer_id", "accounts", ["customer_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("from_account_id", sa.Uuid(), nullable=False),
        sa.Column("to_account_id", sa.Uuid(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'CAD'"), nullable=False),
        sa.Column("status", sa.Unicode(20), nullable=False),
        sa.Column("idempotency_key", sa.Unicode(64), nullable=False),
        sa.Column("correlation_id", sa.Unicode(64), nullable=False),
        sa.Column("failure_reason", sa.Unicode(500), nullable=True),
        sa.Column("created_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.Column("completed_at", DATETIME2(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.ForeignKeyConstraint(["from_account_id"], ["accounts.id"], name="fk_payments_from_account_id_accounts"),
        sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"], name="fk_payments_to_account_id_accounts"),
        sa.CheckConstraint("amount_cents > 0", name=op.f("ck_payments_amount_positive")),
        sa.CheckConstraint("from_account_id <> to_account_id", name=op.f("ck_payments_different_accounts")),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')", name=op.f("ck_payments_status_valid")
        ),
        # Guard #1 (double-click): one payment per sender per idempotency key.
        sa.UniqueConstraint("from_account_id", "idempotency_key", name="uq_payments_sender_idempotency_key"),
    )
    op.create_index("ix_payments_from_account_id", "payments", ["from_account_id"])
    op.create_index("ix_payments_to_account_id", "payments", ["to_account_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.Unicode(6), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("created_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], name="fk_ledger_entries_payment_id_payments"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_ledger_entries_account_id_accounts"),
        sa.CheckConstraint("amount_cents > 0", name=op.f("ck_ledger_entries_amount_positive")),
        sa.CheckConstraint("entry_type IN ('debit', 'credit')", name=op.f("ck_ledger_entries_entry_type_valid")),
        # Guard #2 (duplicate message): at most one debit and one credit per payment.
        sa.UniqueConstraint("payment_id", "entry_type", name="uq_ledger_entries_payment_entry_type"),
    )
    op.create_index("ix_ledger_entries_account_created", "ledger_entries", ["account_id", "created_at"])

    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("message_type", sa.Unicode(50), nullable=False),
        sa.Column("payload", sa.UnicodeText(), nullable=False),
        sa.Column("correlation_id", sa.Unicode(64), nullable=False),
        sa.Column("created_at", DATETIME2(), server_default=UTC_NOW, nullable=False),
        sa.Column("published_at", DATETIME2(), nullable=True),
        sa.Column("publish_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Unicode(500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_messages"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], name="fk_outbox_messages_payment_id_payments"),
    )
    op.create_index("ix_outbox_messages_payment_id", "outbox_messages", ["payment_id"])
    op.create_index("ix_outbox_messages_unpublished", "outbox_messages", ["published_at", "created_at"])


def downgrade() -> None:
    # Reverse order: tables that point at others are dropped first.
    op.drop_table("outbox_messages")
    op.drop_table("ledger_entries")
    op.drop_table("payments")
    op.drop_table("accounts")
    op.drop_table("customers")
