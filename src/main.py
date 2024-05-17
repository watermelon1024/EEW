import logging
import os

from dotenv import load_dotenv

from .client.http import HTTPEEWClient
from .config import Config
from .logging import InterceptHandler, Logging
from .notify.discord import DiscordNotification

load_dotenv()


def main():
    config = Config()
    logger = Logging(
        retention=config["log"]["retention"],
        debug_mode=config["debug-mode"],
        format=config["log"]["format"],
    ).get_logger()
    logging.basicConfig(
        handlers=[InterceptHandler(logger)],
        level=0 if config["debug-mode"] else logging.INFO,
        force=True,
    )

    client = HTTPEEWClient(config, logger)

    if config.get("discord") is None:
        logger.warning("No Discord config provided, Discord notification will not enable.")
    else:
        token = os.getenv("DISCORD_BOT_TOKEN")
        if token is None:
            logger.error("No discord bot token provided.")
            logger.remove()
            exit(1)
        client.add_notification(DiscordNotification(logger, config, token))

    logger.info("Starting EEW client...")
    client.run()
