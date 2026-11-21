"""Balance and transaction history: read-only, always scoped to the logged-in customer's own account."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select
from sqlalchemy.orm import Session, aliased

from northstar_payments.api.auth import current_customer_id
from northstar_payments.api.deps import format_cents, get_own_account, get_session
from northstar_payments.api.schemas import AccountResponse, TransactionItem
from northstar_payments.common.models import Account, EntryType, LedgerEntry, Payment

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/me", response_model=AccountResponse)
def my_account(
    customer_id: uuid.UUID = Depends(current_customer_id),
    session: Session = Depends(get_session),
) -> AccountResponse:
    account = get_own_account(session, customer_id)
    return AccountResponse(
        account_number=account.account_number,
        currency=account.currency,
        balance_cents=account.balance_cents,
        balance=format_cents(account.balance_cents),
    )


@router.get("/me/transactions", response_model=list[TransactionItem])
def my_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    customer_id: uuid.UUID = Depends(current_customer_id),
    session: Session = Depends(get_session),
) -> list[TransactionItem]:
    """Money that actually moved on this account (from the ledger), newest first."""
    account = get_own_account(session, customer_id)
    counterparty = aliased(Account)
    counterparty_id = case(
        (LedgerEntry.entry_type == EntryType.DEBIT.value, Payment.to_account_id),
        else_=Payment.from_account_id,
    )
    rows = session.execute(
        select(LedgerEntry, Payment.status, counterparty.account_number)
        .join(Payment, Payment.id == LedgerEntry.payment_id)
        .join(counterparty, counterparty.id == counterparty_id)
        .where(LedgerEntry.account_id == account.id)
        .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
        .limit(limit)
    ).all()
    return [
        TransactionItem(
            payment_id=entry.payment_id,
            direction=entry.entry_type,
            amount_cents=entry.amount_cents,
            amount=format_cents(entry.amount_cents),
            counterparty_account_number=counterparty_number,
            payment_status=payment_status,
            created_at=entry.created_at,
        )
        for entry, payment_status, counterparty_number in rows
    ]
