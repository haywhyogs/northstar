"""Helpers for integration tests: create isolated test customers, log in, read balances.

Each test creates its own customers with random emails and account numbers, so it never touches
the seeded demo data and tests can't interfere with each other.
"""

import random
import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from northstar_payments.common.db import get_engine
from northstar_payments.common.models import Account, Customer
from northstar_payments.common.security import hash_password

PASSWORD = uuid.uuid4().hex  # random per test run: no password in the code
OPENING_CENTS = 100_000  # $1,000.00


@dataclass
class Person:
    email: str
    account_id: uuid.UUID
    account_number: str


def make_customer() -> Person:
    with Session(get_engine()) as session, session.begin():
        customer = Customer(
            email=f"test-{uuid.uuid4().hex[:12]}@northstar.test",
            full_name="Integration Test",
            password_hash=hash_password(PASSWORD),
        )
        session.add(customer)
        session.flush()
        account = Account(
            customer_id=customer.id,
            account_number=f"T{random.randrange(10**10, 10**11)}",  # 'T' prefix: never clashes with seed 'NS'
            opening_balance_cents=OPENING_CENTS,
            balance_cents=OPENING_CENTS,
        )
        session.add(account)
        session.flush()
        return Person(customer.email, account.id, account.account_number)


def login(client: TestClient, who: Person) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": who.email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def balance(account_id: uuid.UUID) -> int:
    with Session(get_engine()) as session:
        return session.get(Account, account_id).balance_cents
