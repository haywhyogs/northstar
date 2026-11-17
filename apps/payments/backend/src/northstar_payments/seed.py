"""Seed synthetic demo customers, each with one account holding $1,000.00.

Run from apps/payments/backend:   uv run python -m northstar_payments.seed --customers 300

Safe to run twice: customers that already exist (same email) are skipped.
All data is synthetic. Emails use the reserved .test domain, which can never receive real mail.
"""

import argparse
import random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from northstar_payments.common.config import get_settings
from northstar_payments.common.db import get_engine
from northstar_payments.common.models import Account, Customer
from northstar_payments.common.security import hash_password

OPENING_BALANCE_CENTS = 100_000  # $1,000.00 stored as whole cents

FIRST = ["Ada", "Ben", "Chioma", "Dev", "Elena", "Femi", "Grace", "Hiro", "Ines", "Jamal", "Kemi", "Liam"]
LAST = ["Adeyemi", "Brown", "Chen", "Dubois", "Evans", "Fofana", "Garcia", "Hassan", "Ito", "Jones"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=300)
    args = parser.parse_args()

    settings = get_settings()
    if settings.demo_customer_password is None:
        raise SystemExit("Set DEMO_CUSTOMER_PASSWORD in apps/payments/.env first (see .env.example).")
    password = settings.demo_customer_password.get_secret_value()

    rng = random.Random(42)  # fixed seed: the same names every run
    created = 0
    with Session(get_engine()) as session, session.begin():  # one transaction: all or nothing
        existing = set(session.scalars(select(Customer.email)))
        for i in range(1, args.customers + 1):
            email = f"customer{i:04d}@northstar.test"
            if email in existing:
                continue
            customer = Customer(
                email=email,
                full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                password_hash=hash_password(password),
            )
            session.add(customer)
            session.flush()  # gives the customer its id
            session.add(
                Account(
                    customer_id=customer.id,
                    account_number=f"NS{i:010d}",
                    opening_balance_cents=OPENING_BALANCE_CENTS,
                    balance_cents=OPENING_BALANCE_CENTS,
                )
            )
            created += 1

    with Session(get_engine()) as session:
        total = session.scalar(select(func.count()).select_from(Customer))
    print(f"Created {created} customers ({args.customers - created} already existed). Total now: {total}.")


if __name__ == "__main__":
    main()
