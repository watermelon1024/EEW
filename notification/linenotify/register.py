import os

from src import Config, Logger

NAMESPACE = "line-notify"


def register(config: Config, logger: Logger) -> None:
    """
    Register the linenotify notification client.

    Note: DO NOT run or start the client in this function, just register it.
    If you want to run it in the event loop, do it in :method:`NotificationClient.run`.

    :param config: The configuration of linenotify notification client.
    :type config: Config
    :param logger: The logger instance.
    :type logger: Logger
    """
    notify_token = os.getenv("LINENOTIFY_TOKEN")
    if notify_token is None:
        logger.error(f"{NAMESPACE} line-notify token is not set")
        return

    from .linenotify import LineNotifyClient

    return LineNotifyClient(logger, config, notify_token)
