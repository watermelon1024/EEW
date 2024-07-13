import os

from src import Config, Logger

NAMESPACE = "discord-bot"


def register(config: Config, logger: Logger) -> None:
    """
    Register the discord notification client.

    :param config: The configuration of discord bot.
    :type config: Config
    :param logger: The logger instance.
    :type logger: Logger
    """
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token is None:
        raise ValueError("No discord bot token provided.")

    from .bot import DiscordNotification

    return DiscordNotification(logger, config, token)
