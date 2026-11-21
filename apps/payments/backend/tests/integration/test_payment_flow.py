"""The reliability guarantees, tested against a real SQL Server.

API: debit + outbox in one transaction, double-click charges once, overdrafts change nothing.
Worker: a message delivered twice credits once, and the ledger always reconciles with balances.
"""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from northstar_payments.common.db import get_engine
from northstar_payments.common.models import Account, LedgerEntry, OutboxMessage, Payment
from northstar_payments.worker import process_payment
from tests.integration.helpers import OPENING_CENTS, balance, login, make_customer

pytestmark = pytest.mark.integration


def pay(client, headers, to_account: str, cents: int, key: str | None = None):
    return client.post(
        "/payments",
        headers={**headers, "Idempotency-Key": key or uuid.uuid4().hex},
        json={"to_account_number": to_account, "amount_cents": cents},
    )


def test_protected_endpoints_need_a_login(client) -> None:
    assert client.get("/accounts/me").status_code == 401


def test_payment_debits_sender_and_writes_outbox_in_one_go(client, alice, bob) -> None:
    response = pay(client, login(client, alice), bob.account_number, 25_000)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert balance(alice.account_id) == OPENING_CENTS - 25_000
    assert balance(bob.account_id) == OPENING_CENTS  # not credited until the worker runs
    with Session(get_engine()) as session:
        outbox = session.scalars(
            select(OutboxMessage).where(OutboxMessage.payment_id == uuid.UUID(body["payment_id"]))
        ).all()
    assert len(outbox) == 1
    assert outbox[0].correlation_id == body["correlation_id"]
    assert outbox[0].published_at is None  # waiting for the dispatcher


def test_double_click_same_key_charges_once(client, alice, bob) -> None:
    headers = login(client, alice)
    first = pay(client, headers, bob.account_number, 10_000, key="double-click-key")
    second = pay(client, headers, bob.account_number, 10_000, key="double-click-key")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["Idempotent-Replay"] == "true"
    assert second.json()["payment_id"] == first.json()["payment_id"]
    assert balance(alice.account_id) == OPENING_CENTS - 10_000  # debited ONCE


def test_reusing_a_key_for_a_different_payment_is_refused(client, alice, bob) -> None:
    headers = login(client, alice)
    assert pay(client, headers, bob.account_number, 10_000, key="reused-key-1").status_code == 201
    assert pay(client, headers, bob.account_number, 99_00, key="reused-key-1").status_code == 409


def test_insufficient_funds_changes_nothing(client, alice, bob) -> None:
    response = pay(client, login(client, alice), bob.account_number, OPENING_CENTS + 1)

    assert response.status_code == 422
    assert balance(alice.account_id) == OPENING_CENTS
    with Session(get_engine()) as session:
        count = session.scalar(select(func.count()).where(Payment.from_account_id == alice.account_id))
    assert count == 0  # the payment row was rolled back too


def test_unknown_recipient_is_404(client, alice) -> None:
    assert pay(client, login(client, alice), "T00000000000", 1_000).status_code == 404


def test_customers_cannot_see_other_peoples_payments(client, alice, bob) -> None:
    payment_id = pay(client, login(client, alice), bob.account_number, 1_000).json()["payment_id"]
    eve = make_customer()
    assert client.get(f"/payments/{payment_id}", headers=login(client, eve)).status_code == 404


def test_duplicate_message_credits_recipient_once(client, alice, bob) -> None:
    payment_id = uuid.UUID(pay(client, login(client, alice), bob.account_number, 25_000).json()["payment_id"])

    # Service Bus delivers at least once, so simulate the SAME message arriving twice.
    with Session(get_engine()) as session:
        assert process_payment(session, payment_id) == "completed"
    with Session(get_engine()) as session:
        assert process_payment(session, payment_id) == "already completed"

    assert balance(bob.account_id) == OPENING_CENTS + 25_000  # credited ONCE
    with Session(get_engine()) as session:
        credits = session.scalar(
            select(func.count()).where(
                LedgerEntry.payment_id == payment_id, LedgerEntry.entry_type == "credit"
            )
        )
        status = session.get(Payment, payment_id).status
    assert credits == 1
    assert status == "completed"


def test_ledger_reconciles_with_balances(client, alice, bob) -> None:
    headers = login(client, alice)
    for cents in (12_345, 678):
        payment_id = uuid.UUID(pay(client, headers, bob.account_number, cents).json()["payment_id"])
        with Session(get_engine()) as session:
            process_payment(session, payment_id)

    with Session(get_engine()) as session:
        for account_id in (alice.account_id, bob.account_id):
            account = session.get(Account, account_id)
            signed = func.sum(
                func.iif(
                    LedgerEntry.entry_type == "credit", LedgerEntry.amount_cents, -LedgerEntry.amount_cents
                )
            )
            movement = session.scalar(select(signed).where(LedgerEntry.account_id == account_id)) or 0
            assert account.opening_balance_cents + movement == account.balance_cents
