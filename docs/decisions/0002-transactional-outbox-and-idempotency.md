# ADR-0002: Transactional outbox + idempotent worker for payments

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Project owner

## Context
A transfer touches two systems: the **database** (balances) and the **message queue** (Service Bus).
We can't update both in a single all-or-nothing step. If the API debits the sender and then crashes
before sending the message, the recipient is never credited: the exact incident this project is about.
Service Bus also delivers **at least once**, so the same message can arrive more than once.

## Decision
1. **API, one database transaction:** insert the payment (`pending`), debit the sender, and insert an **outbox** row.
2. **Dispatcher:** reads unsent outbox rows, publishes them to Service Bus, then marks them sent.
   If it crashes after publishing but before marking, the message is published again. That's allowed.
3. **Worker:** uses *peek-lock* (receive → process → complete). In **one database transaction** it checks
   whether the payment has already been processed. If not, it credits the recipient and sets the status to `completed`.
   A unique database constraint makes "processed twice" impossible, even if two workers race.
4. **Retries:** if processing throws, the message isn't completed. The lock expires, so Service Bus delivers it again.
   After the queue's *max delivery count*, it moves to the **dead-letter queue** for investigation.

## Alternatives considered
- **Publish directly from the API**: simpler, but loses messages on crashes.
- **Rely on Service Bus duplicate detection**: only works within a time window, isn't in the Basic tier, and doesn't cover worker crashes after crediting.
- **Distributed transactions across DB and queue**: not supported in this setup, and complex.

## Consequences
- ✅ No lost payments and no double credits, even when messages are duplicated.
- ⚠️ Extra moving part (the dispatcher) and a small delay before processing.
- ⚠️ Correctness lives in our database logic, so it must be covered by tests (including a duplicate-delivery test).

## References
- Transactional outbox pattern (Azure Architecture Center, shown with Cosmos DB; the idea is the same): https://learn.microsoft.com/azure/architecture/databases/guide/transactional-outbox-cosmos
- Service Bus message settlement and peek-lock: https://learn.microsoft.com/azure/service-bus-messaging/message-transfers-locks-settlement
- Dead-letter queues: https://learn.microsoft.com/azure/service-bus-messaging/service-bus-dead-letter-queues
