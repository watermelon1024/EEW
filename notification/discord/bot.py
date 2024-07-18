from datetime import datetime

import discord
from discord.ext import tasks

from src import EEW, BaseNotificationClient, Config, Logger

from .message import EEWMessages, NotificationChannel


def void(*args, **kwargs):
    pass


class DiscordNotification(BaseNotificationClient, discord.Bot):
    """
    Represents a discord notification client.
    """

    def __init__(self, logger: Logger, config: Config, token: str) -> None:
        """
        Initialize a new discord notification client.

        :param logger: The logger instance.
        :type logger: Logger
        :param config: The configuration.
        :type config: Config
        :param token: The discord bot token.
        :type token: str
        """
        self.logger = logger
        self.config = config
        self.token = token

        if not config.get("enable-log"):
            logger.disable("discord")  # avoid pycord shard info spamming the console

        self._client_ready = False
        intents = discord.Intents.default()
        owner_ids = config.get("owners")
        discord.Bot.__init__(self, owner_ids=owner_ids, intents=intents)

        # eew-id: EEWMessages
        self.alerts: dict[str, EEWMessages] = {}
        self.notification_channels: list[NotificationChannel] = []

    async def get_or_fetch_channel(self, id: int):
        return self.get_channel(id) or await self.fetch_channel(id)

    async def on_ready(self) -> None:
        """
        The event that is triggered when the bot is ready.
        """
        if self._client_ready:
            return

        for data in self.config["channels"]:
            id = data.get("id")
            try:
                channel = await self.get_or_fetch_channel(id)
            except discord.NotFound:
                self.logger.warning(f"Ignoring channel '{id}': Not found")
                continue
            except discord.Forbidden:
                self.logger.warning(f"Ignoring channel '{id}': No permission to see this channel")
                continue
            if not channel.can_send(discord.Message, discord.Embed, discord.File):
                self.logger.warning(f"Ignoring channel '{id}': No permission to send message")
                continue
            mention = (
                None
                if not (m := data.get("mention"))
                else (f"<@&{m}>" if isinstance(m, int) else f"@{m.removeprefix('@')}")
            )
            self.notification_channels.append({"channel": channel, "mention": mention})
        if not self.notification_channels:
            self.logger.warning("No Discord notification channel available.")
            self.send_eew = void
            self.update_eew = void
            self.lift_eew = void

        self.logger.info(
            "Discord Bot is ready.\n"
            "-------------------------\n"
            f"Logged in as: {self.user.name}#{self.user.discriminator} ({self.user.id})\n"  # type: ignore
            f" API Latency: {self.latency * 1000:.2f} ms\n"
            f"Guilds Count: {len(self.guilds)}\n"
            "-------------------------"
        )
        self._client_ready = True

    async def start(self) -> None:
        self.logger.info("Starting Discord Bot.")
        await discord.Bot.start(self, self.token, reconnect=True)

    async def close(self) -> None:
        await discord.Bot.close(self)
        self.logger.info("Discord Bot closed.")

    async def send_eew(self, eew: EEW):
        m = await EEWMessages.send(self, eew)
        if m is None:
            self.logger.warning("Failed to send EEW message(s).")
            return
        self.alerts[eew.id] = m

        if not self.update_eew_messages_loop.is_running():
            self.update_eew_messages_loop.start()

    async def update_eew(self, eew: EEW):
        m = self.alerts.get(eew.id)
        if m is None:
            await self.send_eew(eew)
            return

        await m.update_eew_data(eew)

    async def lift_eew(self, eew: EEW):
        m = self.alerts.pop(eew.id, None)
        if m is not None:
            await m.lift_eew()

    @tasks.loop(seconds=1)
    async def update_eew_messages_loop(self):
        if not self.alerts:
            self.update_eew_messages_loop.stop()
            return
        now_time = int(datetime.now().timestamp())
        for m in list(self.alerts.values()):
            if now_time > m._lift_time:
                self.loop.create_task(self.lift_eew(m.eew))
            else:
                self.loop.create_task(m.edit())
