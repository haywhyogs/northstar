"""The worker must dead-letter messages it can never process, instead of retrying them forever."""

import uuid
from types import SimpleNamespace

import pytest

from northstar_payments.worker import PermanentError, parse


def message(body: bytes) -> SimpleNamespace:
    return SimpleNamespace(body=iter([body]))


def test_valid_message_gives_the_payment_id() -> None:
    payment_id = uuid.uuid4()
    assert parse(message(f'{{"payment_id": "{payment_id}"}}'.encode())) == payment_id


@pytest.mark.parametrize("body", [b"not json", b"{}", b'{"payment_id": "not-a-uuid"}'])
def test_unreadable_message_is_a_permanent_error(body: bytes) -> None:
    with pytest.raises(PermanentError):
        parse(message(body))
