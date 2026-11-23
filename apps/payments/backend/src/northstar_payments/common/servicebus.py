"""Service Bus client factory, shared by the dispatcher and the worker."""

from azure.servicebus import ServiceBusClient

from northstar_payments.common.config import Settings


def get_servicebus_client(settings: Settings) -> ServiceBusClient:
    # Locally: the emulator's connection string. In Azure: the namespace name + workload identity, no secret.
    if settings.servicebus_connection_string is not None:
        return ServiceBusClient.from_connection_string(
            settings.servicebus_connection_string.get_secret_value()
        )
    if settings.servicebus_namespace is not None:
        from northstar_payments.common.azure import get_credential

        return ServiceBusClient(settings.servicebus_namespace, credential=get_credential())
    raise RuntimeError("Set SERVICEBUS_CONNECTION_STRING (local) or SERVICEBUS_NAMESPACE (Azure)")
