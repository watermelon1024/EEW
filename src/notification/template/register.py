"""
Register the [custom notification client].

This module registers the [custom notification client] with the provided configuration and logger.
The `register` function is the entry point for registering the client. It creates an instance of the `CustomNotificationClient` and returns it.

See also: https://github.com/watermelon1024/EEW/blob/main/docs/zh-TW/dev/notification.md#註冊客戶端
"""

from src import Config, Logger

NAMESPACE = "[custom-notification]"
"the configuration namespace for [custom notification client]"


def register(config: Config, logger: Logger) -> None:
    """
    Register the [custom notification client].

    Note: DO NOT run or start the client in this function, just register it.
    If you want to run it in the event loop, do it in :method:`NotificationClient.run`.

    :param config: The configuration of [custom notification client].
    :type config: Config
    :param logger: The logger instance.
    :type logger: Logger
    """
    from .main import CustomNotificationClient

    ...
    return CustomNotificationClient(logger, config)
