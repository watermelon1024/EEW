import asyncio
from datetime import datetime
import math

import discord
from discord.ext import tasks

from ..config import Config
from ..earthquake.eew import EEW
from ..logging import Logger
from ..utils import MISSING
from .abc import NotificationClient


class EEWMessages:
    """
    Represents discord messages with EEW data.
    """

    __slots__ = (
        "bot",
        "eew",
        "messages",
        "_info_embed",
        "_intensity_embed",
        "map_url",
        "_bot_ping",
    )

    def __init__(
        self, bot: "DiscordNotification", eew: EEW, messages: list[discord.Message]
    ) -> None:
        """
        Initialize a new discord message.

        :param bot: The discord bot.
        :type bot: DiscordNotification
        :param eew: The EEW instance.
        :type eew: EEW
        :param message: The discord message.
        :type message: discord.Message
        """
        self.bot = bot
        self.eew = eew
        self.messages = messages
        self._info_embed: discord.Embed = None
        self._intensity_embed: discord.Embed = None
        self.map_url: str = None
        self._bot_ping: float = self.bot.latency

    def info_embed(self) -> discord.Embed:
        # shortcut
        eew = self.eew
        eq = eew._earthquake

        self._info_embed = discord.Embed(
            title=f"地震速報　第 {eew.serial} 報{'（最終報）' if eew.final else ''}",
            description=f"""\
<t:{int(eq.time.timestamp())}:T> {f"於 {eq.location.display_name} " if eq.location.display_name else ""}發生有感地震，慎防搖晃！
預估規模 `{eq.mag}`，震源深度 `{eq.depth}` 公里，最大震度{eq.max_intensity.display}
發報單位．{eew.provider.display_name}｜發報時間．<t:{int(eew.time.timestamp())}:T>""",
            color=0xFF0000,
        ).set_author(
            name="Taiwan Earthquake Early Warning",
            icon_url="https://cdn.discordapp.com/emojis/1018381096532070572.png",
        )

        return self._info_embed

    def intensity_embed(self) -> discord.Embed:
        if math.isfinite(ping := self.bot.latency):
            self._bot_ping = ping
        current_time = int(datetime.now().timestamp() + self._bot_ping)
        self._intensity_embed = discord.Embed(
            title="震度等級預估",
            description="各縣市預估最大震度｜預計抵達時間\n"
            + "\n".join(
                (
                    f"{city} {intensity.region.name.ljust(4, '　')} {intensity.intensity.display}｜"
                    + (
                        f"<t:{arrival_time}:R>抵達"
                        if (arrival_time := int(intensity.distance.s_time.timestamp()))
                        > current_time
                        else "⚠️已抵達"
                    )
                )
                for city, intensity in self.eew.earthquake.city_max_intensity.items()
                if intensity.intensity.value > 0
            ),
            color=0xF39C12,
        ).set_image(url="attachment://image.png")

        return self._intensity_embed

    async def _send_singal_message(self, channel: discord.TextChannel, mention: str = None):
        try:
            return await channel.send(mention, embed=self._info_embed)
        except Exception as e:
            self.bot.logger.exception(f"Failed to send message in {channel.name}", exc_info=e)
            return None

    async def _edit_singal_message(self, message: discord.Message, map_embed: discord.Embed):
        try:
            return await message.edit(embeds=[self._info_embed, map_embed])
        except Exception as e:
            self.bot.logger.exception(f"Failed to edit message {message.id}", exc_info=e)
            return None

    @classmethod
    async def send(
        cls,
        bot: "DiscordNotification",
        eew: EEW,
        notification_channels: list[dict[str, str | discord.TextChannel | None]],
    ) -> "EEWMessages":
        """
        Send a new discord message.

        :param eew: The EEW instance.
        :type eew: EEW
        :param channels: Discord channels.
        :type channels: list[discord.TextChannel]
        :param mention: The mention to send.
        :type mention: str
        :return: The new discord messages.
        :rtype: EEWMessage
        """
        self = cls(bot, eew, [])
        self.info_embed()
        self.messages = list(
            filter(
                None,
                await asyncio.gather(
                    *(
                        self._send_singal_message(d["channel"], d["mention"])
                        for d in notification_channels
                    )
                ),
            )
        )
        if not self.messages:
            return None
        return self

    async def edit(self) -> None:
        """
        Edit the discord messages to update S wave arrival time.
        """
        intensity_embed = self.intensity_embed()
        if not self.map_url:
            m = await self.messages[0].edit(
                embeds=[self._info_embed, intensity_embed],
                file=discord.File(self.eew.earthquake.intensity_map, "image.png"),
            )
            self.map_url = m.embeds[1].image.url
            update = ()
            intensity_embed = self.intensity_embed()
        else:
            update = (self._edit_singal_message(self.messages[0], intensity_embed.copy()),)
        intensity_embed.set_image(url=self.map_url)

        await asyncio.gather(
            *update,
            *(self._edit_singal_message(msg, intensity_embed) for msg in self.messages[1:]),
        )

    async def update_eew_data(self, eew: EEW) -> "EEWMessages":
        """
        Update EEW data.

        :param eew: The EEW instance.
        :type eew: EEW
        """
        self.eew = eew
        self.map_url = None
        self.info_embed()
        eew.earthquake.calc_city_max_intensity()
        eew.earthquake.draw_map()

        return self


class DiscordNotification(NotificationClient, discord.Bot):
    """
    Represents a discord notification client.
    """

    # eew-id: EEWMessages
    alerts: dict[str, EEWMessages] = {}
    notification_channels: list[dict[str, str | discord.TextChannel | None]] = []

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

        logger.disable("discord")  # avoid pycord shard info spamming the console

        self._client_ready = False
        intents = discord.Intents.default()
        owner_ids = config["discord"].get("owners")
        super().__init__(owner_ids=owner_ids, intents=intents)

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

        for data in self.config["discord"]["channels"]:
            channel = await self.get_or_fetch_channel(data["id"], None)
            if channel is None:
                self.logger.warning(f"Ignore channel '{data['id']}' because it was not found.")
                continue
            mention = (
                None
                if not (m := data.get("mention"))
                else (f"<@&{m}>" if isinstance(m, int) else f"@{m.removeprefix('@')}")
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

    async def run(self) -> None:
        return await super().start(self.token, reconnect=True)

    async def close(self) -> None:
        await super().close()
        self.logger.info("Discord Bot closed.")

    async def send_eew(self, eew: EEW) -> EEWMessages:
        m = await EEWMessages.send(self, eew, self.notification_channels)
        self.alerts[eew.id] = m

        eew.earthquake.calc_city_max_intensity()
        eew.earthquake.draw_map()

        if not self.update_eew_messages_loop.is_running():
            self.update_eew_messages_loop.start()

        return m

    async def update_eew(self, eew: EEW) -> EEWMessages:
        m = self.alerts.get(eew.id)
        if m is None:
            return await self.send_eew(eew)

        return await m.update_eew_data(eew)

    async def lift_eew(self, eew: EEW):
        self.alerts.pop(eew.id, None)

    @tasks.loop(seconds=1)
    async def update_eew_messages_loop(self):
        if not self.alerts:
            self.update_eew_messages_loop.stop()
            return

        for m in self.alerts.values():
            await m.edit()
