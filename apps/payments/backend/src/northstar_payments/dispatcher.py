"""Outbox dispatcher (the 'mail runner'): outbox_messages -> Service Bus queue.

Run: uv run python -m northstar_payments.dispatcher

Loop: lock a batch of unsent outbox rows -> send each to Service Bus -> mark it sent -> commit.
If we crash after sending but before committing, the row is sent AGAIN next time. That's at-least-once
delivery, and it's safe because the worker ignores payments it has already completed (guard #2).
"""

import logging

from azure.servicebus import ServiceBusMessage
from azure.servicebus.exceptions import ServiceBusError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from northstar_payments.common.config import get_settings
from northstar_payments.common.db import get_engine
from northstar_payments.common.logging import configure_logging, correlation_id_var
from northstar_payments.common.models import OutboxMessage
from northstar_payments.common.servicebus import get_servicebus_client
from northstar_payments.common.shutdown import install_signal_handlers, stop_requested

logger = logging.getLogger("northstar_payments.dispatcher")

# UPDLOCK + READPAST: if several dispatchers run, each takes different rows and skips rows another has locked.
LOCK_HINT = "WITH (UPDLOCK, ROWLOCK, READPAST)"


def dispatch_batch(session: Session, sender, batch_size: int) -> int:
    """Publish one batch. Returns how many rows were sent."""
    rows = session.scalars(
        select(OutboxMessage)
        .with_hint(OutboxMessage, LOCK_HINT)
        .where(OutboxMessage.published_at.is_(None))
        .order_by(OutboxMessage.created_at)
        .limit(batch_size)
    ).all()
    sent = 0
    for row in rows:
        token = correlation_id_var.set(row.correlation_id)
        try:
            sender.send_messages(
                ServiceBusMessage(
                    row.payload,
                    message_id=str(row.id),  # lets anyone trace a queue message back to its outbox row
                    correlation_id=row.correlation_id,
                    content_type="application/json",
                    application_properties={"message_type": row.message_type},
                )
            )
            row.published_at = func.sysutcdatetime()
            sent += 1
            logger.info("outbox message published", extra={"fields": {"payment_id": str(row.payment_id)}})
        except ServiceBusError as error:  # unreachable, throttled, ...: keep the row, try again later
            row.publish_attempts += 1
            row.last_error = str(error)[:500]
            logger.warning(
                "outbox publish failed",
                extra={"fields": {"payment_id": str(row.payment_id), "attempts": row.publish_attempts}},
            )
        finally:
            correlation_id_var.reset(token)
    session.commit()
    return sent


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    install_signal_handlers()
    logger.info("dispatcher started", extra={"fields": {"queue": settings.servicebus_queue}})

    with (
        get_servicebus_client(settings) as client,
        client.get_queue_sender(settings.servicebus_queue) as sender,
    ):
        while not stop_requested.is_set():
            try:
                with Session(get_engine()) as session:
                    sent = dispatch_batch(session, sender, settings.dispatcher_batch_size)
            except Exception:
                logger.exception("dispatcher loop error (database unreachable?)")
                sent = 0
            if sent == 0:
                stop_requested.wait(settings.dispatcher_idle_seconds)  # nothing to do: pause briefly
    logger.info("dispatcher stopped")


if __name__ == "__main__":
    main()
