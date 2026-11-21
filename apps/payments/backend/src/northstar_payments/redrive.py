"""Operator tool: move dead-lettered payment messages back to the main queue ("redrive").

List only (default):  python -m northstar_payments.redrive
Redrive:              python -m northstar_payments.redrive --apply

Safe to run more than once: the worker credits each payment at most once (guard #2), so a message that
was already processed is simply skipped. Fix the CAUSE first (worker down, bad deploy), then redrive.
Runbook: docs/runbooks/dead-letter-redrive.md
"""

import argparse
import logging

from azure.servicebus import ServiceBusMessage, ServiceBusSubQueue

from northstar_payments.common.config import get_settings
from northstar_payments.common.logging import configure_logging, correlation_id_var
from northstar_payments.common.servicebus import get_servicebus_client

logger = logging.getLogger("northstar_payments.redrive")


def _text(value: object) -> object:
    return value.decode() if isinstance(value, bytes) else value


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="actually move messages (default: list only)")
    parser.add_argument("--max", type=int, default=100, help="maximum messages to handle")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    logging.getLogger("azure").setLevel(logging.WARNING)  # hide the SDK's connection chatter
    queue = settings.servicebus_queue

    with get_servicebus_client(settings) as client:
        dead_letters = client.get_queue_receiver(
            queue, sub_queue=ServiceBusSubQueue.DEAD_LETTER, max_wait_time=5
        )
        with dead_letters:
            if not args.apply:
                messages = dead_letters.peek_messages(max_message_count=args.max)  # look, don't touch
                for m in messages:
                    logger.info(
                        "dead-lettered message",
                        extra={
                            "fields": {
                                "message_id": str(m.message_id),
                                "correlation_id": m.correlation_id,
                                "reason": m.dead_letter_reason,
                                "description": m.dead_letter_error_description,
                            }
                        },
                    )
                logger.info(
                    f"{len(messages)} message(s) in the dead-letter queue. Re-run with --apply to redrive."
                )
                return

            moved = 0
            with client.get_queue_sender(queue) as sender:
                while moved < args.max:
                    batch = dead_letters.receive_messages(max_message_count=min(20, args.max - moved))
                    if not batch:
                        break
                    for m in batch:
                        token = correlation_id_var.set(m.correlation_id or str(m.message_id))
                        try:
                            sender.send_messages(
                                ServiceBusMessage(
                                    b"".join(m.body),
                                    message_id=str(m.message_id),
                                    correlation_id=m.correlation_id,
                                    content_type=m.content_type,
                                    application_properties={
                                        _text(k): _text(v)
                                        for k, v in (m.application_properties or {}).items()
                                    },
                                )
                            )
                            dead_letters.complete_message(
                                m
                            )  # remove from the DLQ only after the copy is queued
                            moved += 1
                            logger.info(
                                "message redriven", extra={"fields": {"message_id": str(m.message_id)}}
                            )
                        finally:
                            correlation_id_var.reset(token)
            logger.info(f"redrive finished: {moved} message(s) moved back to '{queue}'")


if __name__ == "__main__":
    main()
