"""Fast checks with no database: money formatting and password hashing."""

import pytest

from northstar_payments.api.deps import format_cents
from northstar_payments.common.security import hash_password, verify_password


@pytest.mark.parametrize(
    ("cents", "text"),
    [(0, "0.00"), (5, "0.05"), (25000, "250.00"), (123456789, "1234567.89"), (-150, "-1.50")],
)
def test_format_cents_uses_whole_number_maths(cents: int, text: str) -> None:
    assert format_cents(cents) == text


def test_password_hash_verifies_only_the_right_password() -> None:
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong horse", stored)


def test_same_password_gives_different_hashes_because_of_salt() -> None:
    assert hash_password("same") != hash_password("same")


def test_password_is_never_stored_in_plain_text() -> None:
    assert "plain-secret" not in hash_password("plain-secret")


def test_malformed_stored_hash_is_rejected_not_crashing() -> None:
    assert not verify_password("anything", "not-a-real-hash")
