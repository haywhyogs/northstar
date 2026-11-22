# Runbook: payments stuck in the dead-letter queue

**Symptom:** a payment stays `pending`; the sender was debited but the recipient wasn't credited.
**Alert (planned):** dead-letter message count > 0 on the `payments` queue.

## 1. Find out why messages were dead-lettered
```bash
# Local (Compose):
docker compose exec worker python -m northstar_payments.redrive
# AKS:
kubectl -n payments-<env> exec deploy/worker -- python -m northstar_payments.redrive
```
Each line shows the `reason` and the payment's `correlation_id`.

| Reason | Meaning | Fix the cause first |
|---|---|---|
| `TTLExpiredException` | No worker processed it before the message's time-to-live ran out | Worker down or crash-looping: restore it, check its logs |
| `MaxDeliveryCountExceeded` | The worker tried and failed repeatedly | Read the worker's ERROR lines for that `correlation_id` (database down? bug?) |
| `PermanentError` | Our worker rejected it as unprocessable | Investigate before redriving: it will fail again |

## 2. Redrive
```bash
docker compose exec worker python -m northstar_payments.redrive --apply
```
Safe to repeat: the worker credits each payment at most once (database rule `uq_ledger_entries_payment_entry_type`).

## 3. Verify
- The payment shows `completed`; the recipient's balance increased **once**.
- The dead-letter count is back to 0.
- Write an incident note in `docs/incidents/` if customers were affected.

## Prevention
- Alert on dead-letter count > 0 and on "payment pending > N minutes".
- Set the queue's message time-to-live **longer than the worst outage you'd tolerate**. The local emulator uses 1 hour;
  the Azure queue is configured in Terraform.
- Workers reconnect on connection loss, and the platform restarts crashed containers.
