"""Send money. The sender is debited NOW; the worker credits the recipient later (ADR-0002).

One database transaction writes: the payment (pending) + the sender's debit + the outbox message.
Either all three are saved, or none are.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from northstar_payments.api.auth import current_customer_id
from northstar_payments.api.deps import format_cents, get_own_account, get_session
from northstar_payments.api.schemas import PaymentRequest, PaymentResponse
from northstar_payments.common.logging import correlation_id_var
from northstar_payments.common.models import (
    Account,
    EntryType,
    LedgerEntry,
    OutboxMessage,
    Payment,
    PaymentStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

MESSAGE_TYPE = "PaymentRequested"


def _to_response(session: Session, payment: Payment) -> PaymentResponse:
    numbers = dict(
        session.execute(
            select(Account.id, Account.account_number).where(
                Account.id.in_([payment.from_account_id, payment.to_account_id])
            )
        ).all()
    )
    return PaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        amount_cents=payment.amount_cents,
        amount=format_cents(payment.amount_cents),
        currency=payment.currency,
        from_account_number=numbers[payment.from_account_id],
        to_account_number=numbers[payment.to_account_id],
        correlation_id=payment.correlation_id,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
    )


def _find_by_key(session: Session, sender_id: uuid.UUID, idempotency_key: str) -> Payment | None:
    return session.scalar(
        select(Payment).where(
            Payment.from_account_id == sender_id, Payment.idempotency_key == idempotency_key
        )
    )


def _replay(session: Session, existing: Payment, body: PaymentRequest, response: Response) -> PaymentResponse:
    """Same Idempotency-Key again (double-click, network retry): return the ORIGINAL payment, change nothing."""
    original = _to_response(session, existing)
    if (original.amount_cents, original.to_account_number) != (body.amount_cents, body.to_account_number):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Idempotency-Key was already used for a different payment"
        )
    response.status_code = status.HTTP_200_OK
    response.headers["Idempotent-Replay"] = "true"
    logger.info("payment replayed", extra={"fields": {"payment_id": str(existing.id)}})
    return original


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentRequest,
    response: Response,
    # The browser generates one key per "Send" click and reuses it on retries (guard #1 against duplicates).
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=64),
    customer_id: uuid.UUID = Depends(current_customer_id),
    session: Session = Depends(get_session),
) -> PaymentResponse:
    sender = get_own_account(session, customer_id)

    existing = _find_by_key(session, sender.id, idempotency_key)
    if existing is not None:
        return _replay(session, existing, body, response)

    recipient = session.scalar(select(Account).where(Account.account_number == body.to_account_number))
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipient account not found")
    if recipient.id == sender.id:
        raise HTTPException(422, "Cannot send money to your own account")

    payment = Payment(
        id=uuid.uuid4(),
        from_account_id=sender.id,
        to_account_id=recipient.id,
        amount_cents=body.amount_cents,
        status=PaymentStatus.PENDING.value,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id_var.get() or str(uuid.uuid4()),
    )
    try:
        session.add(payment)
        session.flush()  # INSERT now: a concurrent duplicate key fails here (unique constraint)

        # Debit only if the money is there. Checked and changed in ONE statement, so two simultaneous
        # payments can't both spend the same balance. (The CHECK constraint is the last line of defence.)
        debited = session.execute(
            update(Account)
            .where(Account.id == sender.id, Account.balance_cents >= body.amount_cents)
            .values(
                balance_cents=Account.balance_cents - body.amount_cents,
                updated_at=func.sysutcdatetime(),
            )
            .execution_options(synchronize_session=False)
        ).rowcount
        if debited != 1:
            session.rollback()
            raise HTTPException(422, "Insufficient funds")

        session.add(
            LedgerEntry(
                payment_id=payment.id,
                account_id=sender.id,
                entry_type=EntryType.DEBIT.value,
                amount_cents=body.amount_cents,
            )
        )
        session.add(
            OutboxMessage(
                id=uuid.uuid4(),
                payment_id=payment.id,
                message_type=MESSAGE_TYPE,
                correlation_id=payment.correlation_id,
                payload=json.dumps({"payment_id": str(payment.id), "correlation_id": payment.correlation_id}),
            )
        )
        session.commit()  # all three rows saved together, or none
    except IntegrityError:
        # Another request with the same key won the race. Return its payment instead.
        session.rollback()
        existing = _find_by_key(session, sender.id, idempotency_key)
        if existing is None:
            raise
        return _replay(session, existing, body, response)

    logger.info(
        "payment accepted",
        extra={
            "fields": {"payment_id": str(payment.id), "amount_cents": body.amount_cents, "status": "pending"}
        },
    )
    session.refresh(payment)
    return _to_response(session, payment)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: uuid.UUID,
    customer_id: uuid.UUID = Depends(current_customer_id),
    session: Session = Depends(get_session),
) -> PaymentResponse:
    """Status of a payment the customer sent or received. Anyone else gets 404 (we don't reveal it exists)."""
    account = get_own_account(session, customer_id)
    payment = session.scalar(
        select(Payment).where(
            Payment.id == payment_id,
            or_(Payment.from_account_id == account.id, Payment.to_account_id == account.id),
        )
    )
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return _to_response(session, payment)
