"""Payment worker (the 'back-office clerk'): Service Bus queue -> credit the recipient.

Run: uv run python -m northstar_payments.worker

For each message, in ONE database transaction: lock the payment -> already completed? skip (guard #2)
-> otherwise credit the recipient, add the credit ledger entry, mark the payment completed.
Then tell Service Bus the message is done ('complete'). Messages are received in peek-lock mode:
if the worker crashes before completing, the lock expires and the message is delivered again.
"""

import json
import logging
import uuid

from azure.servicebus import ServiceBusReceivedMessage
from azure.servicebus.exceptions import ServiceBusError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from northstar_payments.common.config import get_settings
from northstar_payments.common.db import get_engine
from northstar_payments.common.logging import configure_logging, correlation_id_var
from northstar_payments.common.models import Account, EntryType, LedgerEntry, Payment, PaymentStatus
from northstar_payments.common.servicebus import get_servicebus_client
from northstar_payments.common.shutdown import install_signal_handlers, stop_requested

logger = logging.getLogger("northstar_payments.worker")
RECONNECT_SECONDS = 5


class PermanentError(Exception):
    """Retrying can never fix this message (bad content, unknown payment): send it to the dead-letter queue."""


def parse(message: ServiceBusReceivedMessage) -> uuid.UUID:
    try:
        body = json.loads(b"".join(message.body))
        return uuid.UUID(body["payment_id"])
    except (ValueError, KeyError, TypeError) as error:
        raise PermanentError(f"unreadable message: {error}") from error


def process_payment(session: Session, payment_id: uuid.UUID) -> str:
    """Credit the recipient exactly once. Returns 'completed' or 'already completed'."""
    payment = session.scalar(
        select(Payment).with_hint(Payment, "WITH (UPDLOCK, ROWLOCK)").where(Payment.id == payment_id)
    )  # the lock makes a second worker with the same message wait here, then see 'completed'
    if payment is None:
        raise PermanentError(f"payment {payment_id} not found")
    if payment.status == PaymentStatus.COMPLETED.value:
        session.rollback()
        return "already completed"

    session.add(
        LedgerEntry(
            payment_id=payment.id,
            account_id=payment.to_account_id,
            entry_type=EntryType.CREDIT.value,
            amount_cents=payment.amount_cents,
        )
    )
    session.execute(
        update(Account)
        .where(Account.id == payment.to_account_id)
        .values(balance_cents=Account.balance_cents + payment.amount_cents, updated_at=func.sysutcdatetime())
        .execution_options(synchronize_session=False)
    )
    payment.status = PaymentStatus.COMPLETED.value
    payment.completed_at = func.sysutcdatetime()
    payment.updated_at = func.sysutcdatetime()
    try:
        session.commit()
    except IntegrityError:
        # Database guard #2 (one credit per payment) fired: another delivery already credited it.
        session.rollback()
        return "already completed"
    return "completed"


def handle(receiver, message: ServiceBusReceivedMessage) -> None:
    token = correlation_id_var.set(message.correlation_id or str(message.message_id))
    fields = {"message_id": str(message.message_id), "delivery_count": message.delivery_count}
    try:
        payment_id = parse(message)
        fields["payment_id"] = str(payment_id)
        with Session(get_engine()) as session:
            outcome = process_payment(session, payment_id)
        receiver.complete_message(message)  # done: remove it from the queue
        logger.info(f"payment {outcome}", extra={"fields": fields})
    except PermanentError as error:
        receiver.dead_letter_message(message, reason="PermanentError", error_description=str(error)[:1000])
        logger.error("message dead-lettered", extra={"fields": {**fields, "reason": str(error)}})
    except Exception:
        # Temporary problem (database down, deadlock...): give it back. Service Bus retries it, and after
        # MaxDeliveryCount attempts moves it to the dead-letter queue automatically.
        receiver.abandon_message(message)
        logger.exception("payment processing failed, will retry", extra={"fields": fields})
    finally:
        correlation_id_var.reset(token)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    install_signal_handlers()
    logger.info("worker started", extra={"fields": {"queue": settings.servicebus_queue}})

    while not stop_requested.is_set():
        try:
            with (
                get_servicebus_client(settings) as client,
                client.get_queue_receiver(settings.servicebus_queue) as receiver,
            ):
                logger.info("connected to Service Bus")
                while not stop_requested.is_set():
                    for message in receiver.receive_messages(max_message_count=10, max_wait_time=5):
                        handle(receiver, message)
        except ServiceBusError:
            # Connection dropped (idle timeout, network blip, Service Bus restart): reconnect, don't crash.
            # Unfinished messages are safe: their locks expire and Service Bus delivers them again.
            logger.warning("Service Bus connection lost, reconnecting in 5 seconds", exc_info=True)
            stop_requested.wait(RECONNECT_SECONDS)
    logger.info("worker stopped")


if __name__ == "__main__":
    main()
