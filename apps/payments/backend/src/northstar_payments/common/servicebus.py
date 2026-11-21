"""Service Bus client factory, shared by the dispatcher and the worker."""

from azure.servicebus import ServiceBusClient

from northstar_payments.common.config import Settings


def get_servicebus_client(settings: Settings) -> ServiceBusClient:
    if settings.servicebus_connection_string is None:
        # Passwordless (Entra ID / AKS workload identity) is added with the AKS platform.
        raise RuntimeError("SERVICEBUS_CONNECTION_STRING is not set. Check apps/payments/.env")
    return ServiceBusClient.from_connection_string(settings.servicebus_connection_string.get_secret_value())
