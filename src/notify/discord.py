import asyncio

import discord

from ..earthquake.eew import EEW
from ..logging import Logger
from ..utils import MISSING
from .abc import NotificationClient


class EEWMessages:
    """
    Represents discord messages with EEW data.
    """

    __slots__ = ("eew", "messages")
    _embed_cache = None

    def __init__(self, eew: EEW, message: discord.Message) -> None:
        """
        Initialize a new discord message.

        :param eew: The EEW instance.
        :type eew: EEW
        :param message: The discord message.
        :type message: discord.Message
        """
        self.eew = eew
        self.message = message

    def embed(self):
        if self._embed_cache is not None:
            return self._embed_cache

        # shortcut
        eew = self.eew
        eq = eew.earthquake
        self._embed_cache = discord.Embed(
            title=f"地震速報　第{eew.serial}報{'(最終報)' if eew.final else ''}",
            description=f"""\
{eq.time.strftime("%m/%d %H:%M:%S")} 左右{f"於 {eq.location.display_name}附近 " if eq.location.display_name else ""}發生有感地震，慎防搖晃。
預估規模`{eq.mag}`，震源深度 {eq.depth}公里，最大震度{eq.max_intensity.display}""",
            color=0xFF0000,
        ).set_author(
            name="Taiwan Earthquake Early Warning",
            icon_url="https://cdn.discordapp.com/emojis/1018381096532070572.png",
        )
        return self._embed_cache

    @classmethod
    async def send(
        cls, eew: EEW, channel: discord.TextChannel, mention: str = None
    ) -> "EEWMessages":
        """
        Send a new discord message.

        :param eew: The EEW instance.
        :type eew: EEW
        :param channel: The discord channel.
        :type channel: discord.TextChannel
        :param mention: The mention to send.
        :type mention: str
        :return: The new discord message.
        :rtype: EEWMessage
        """
        message = await channel.send(mention)
        return cls(eew, message)


class DiscordNotification(NotificationClient, discord.Bot):
    """
    Represents a discord notification client.
    """

    # eew-id: EEWMessages
    alerts: dict[str, EEWMessages] = {}

    def __init__(self, logger: Logger, config: dict, token: str) -> None:
        """
        Initialize a new discord notification client.

        :param logger: The logger instance.
        :type logger: Logger
        :param config: The configuration.
        :type config: dict
        :param token: The discord bot token.
        :type token: str
        """
        self.logger = logger
        self.config = config

        logger.disable("discord")  # avoid pycord shard info spamming the console

        self._client_ready = False
        intents = discord.Intents.default()
        super().__init__(owner_ids=self.config["discord"]["owners"], intents=intents)
        asyncio.create_task(self.start(token))

    async def get_or_fetch_channel(self, id: int, default=MISSING):
        try:
            return self.get_channel(id) or await self.fetch_channel(id)
        except Exception as e:
            if default is not MISSING:
                return default
            raise e

    async def on_ready(self) -> None:
        """
        The event that is triggered when the bot is ready.
        """
        if self._client_ready:
            return

        self.notification_channels: list[dict] = []
        for data in self.config["discord"]["channels"]:
            channel = await self.get_or_fetch_channel(data["id"])
            if channel is None:
                self.logger.warning(f"Ignore channel '{data['id']}' because it was not found.")
                continue
            mention = (
                f"@{m}"
                if (m := data.get("mention", "everyone").removeprefix("@")) in ["everyone", "here"]
                else f"<@&{m}>"
            )
            self.notification_channels.append({"channel": channel, "mention": mention})

        self.logger.info(
            f"""Discord Bot started.
-------------------------
Logged in as: {self.user.name}#{self.user.discriminator} ({self.user.id})
 API Latency: {self.latency * 1000:.2f} ms
Guilds Count: {len(self.guilds)}
-------------------------"""
        )
        self._client_ready = True

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        return await super().start(token, reconnect=reconnect)

    async def close(self) -> None:
        await super().close()
        self.logger.info("Discord Bot closed.")

    async def send_eew(self, eew: EEW):
        return await super().send_eew(eew)
