import asyncio
import math
import os
from datetime import datetime
from typing import Optional, TypedDict

import discord
from discord.ext import tasks

from src import EEW, MISSING, BaseNotificationClient, Config, Logger


class NotifyAndChannel(TypedDict):
    channel: discord.TextChannel
    mention: Optional[str]


class _SingleMessage:
    """
    Represents a single message.
    """

    __slots__ = ("message", "mention")

    def __init__(self, message: discord.Message, mention: Optional[str]) -> None:
        self.message = message
        self.mention = mention

    @property
    def edit(self):
        return self.message.edit


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
        "_region_intensity",
        "map_url",
        "_bot_latency",
        "_lift_time",
        "_last_update",
        "_map_update_interval",
    )

    def __init__(self, bot: "DiscordNotification", eew: EEW, messages: list[_SingleMessage]) -> None:
        """
        Initialize a new discord message.

        :param bot: The discord bot.
        :type bot: DiscordNotification
        :param eew: The EEW instance.
        :type eew: EEW
        :param message: The discord message.
        :type message: _SingleMessage
        """
        self.bot = bot
        self.eew = eew
        self.messages = messages

        self._info_embed: Optional[discord.Embed] = None
        self._intensity_embed = None
        self._region_intensity: Optional[dict[tuple[str, str], tuple[str, int]]] = None
        self.map_url: Optional[str] = None
        self._bot_latency: float = 0
        self._lift_time = eew.earthquake.time.timestamp() + 120  # 2min
        self._last_update: float = 0
        self._map_update_interval: float = 1

    def info_embed(self) -> discord.Embed:
        # shortcut
        eew = self.eew
        eq = eew._earthquake

        self._info_embed = discord.Embed(
            title=f"地震速報　第 {eew.serial} 報{'（最終報）' if eew.final else ''}",
            description=f"""\
<t:{int(eq.time.timestamp())}:T> 於 {eq.location.display_name or ""}(`{eq.lon:.2f}`, `{eq.lat:.2f}`) 發生有感地震，慎防搖晃！
預估規模 `{eq.mag}`，震源深度 `{eq.depth}` 公里，最大震度{eq.max_intensity.display}
發報單位．{eew.provider.display_name}｜發報時間．<t:{int(eew.time.timestamp())}:T>""",
            color=0xFF0000,
        ).set_author(
            name="Taiwan Earthquake Early Warning",
            icon_url="https://raw.githubusercontent.com/watermelon1024/EEW/main/asset/logo_small.png",
        )

        return self._info_embed

    def get_latency(self) -> float:
        """
        Get the bot latency.
        """
        if math.isfinite(ping := self.bot.latency):
            self._bot_latency = ping
        return self._bot_latency

    def intensity_embed(self) -> discord.Embed:
        if self.eew.earthquake.city_max_intensity is None:
            return self._intensity_embed
        if self._region_intensity is None:
            self.get_region_intensity()

        current_time = int(datetime.now().timestamp() + self.get_latency())
        self._intensity_embed = discord.Embed(
            title="震度等級預估",
            description="各縣市預估最大震度｜預計抵達時間\n"
            + "\n".join(
                f"{city} {town} {intensity}｜{f'<t:{time}:R>抵達' if time > current_time else '⚠️已抵達'}"
                for (city, town), (intensity, time) in self._region_intensity.items()
            )
            + f"\n上次更新：<t:{current_time}:T> (<t:{current_time}:R>)",
            color=0xF39C12,
            image="attachment://image.png",
        ).set_footer(text="僅供參考，實際情況以氣象署公布之資料為準")

        return self._intensity_embed

    def get_region_intensity(self):
        self._region_intensity = {
            (city, intensity.region.name.ljust(4, "　")): (
                intensity.intensity.display,
                int(intensity.distance.s_arrival_time.timestamp()),
            )
            for city, intensity in self.eew.earthquake.city_max_intensity.items()
            if intensity.intensity.value > 0
        }
        # self._lift_time = max(x[1] for x in self._region_intensity.values()) + 10

        return self._region_intensity

    async def _send_singal_message(self, channel: discord.TextChannel, mention: Optional[str] = None):
        eq = self.eew.earthquake
        try:
            return _SingleMessage(
                await channel.send(
                    f"{mention or ''} {eq.time.strftime('%H:%M:%S')} 於 {eq.location.display_name or eq.location} 發生規模`{eq.mag}`有感地震，慎防搖晃！",
                ),
                mention,
            )
        except Exception as e:
            self.bot.logger.exception(f"Failed to send message in {channel.name}", exc_info=e)
            return None

    async def _edit_singal_message(self, message: _SingleMessage, intensity_embed: discord.Embed, **kwargs):
        try:
            return await message.edit(content=message.mention, embeds=[self._info_embed, intensity_embed], **kwargs)  # type: ignore
        except Exception as e:
            self.bot.logger.exception(f"Failed to edit message {message.message.id}", exc_info=e)
            return None

    @classmethod
    async def send(
        cls,
        bot: "DiscordNotification",
        eew: EEW,
        notification_channels: list[NotifyAndChannel],
    ) -> Optional["EEWMessages"]:
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
        self.messages = list(
            filter(
                None,
                await asyncio.gather(
                    *(self._send_singal_message(d["channel"], d["mention"]) for d in notification_channels)
                ),
            )
        )
        if not self.messages:
            return None

        self._info_embed = self.info_embed()
        self._intensity_embed = discord.Embed(title="震度等級預估", description="計算中...")
        return self

    async def edit(self) -> None:
        """
        Edit the discord messages to update S wave arrival time.
        """
        intensity_embed = self.intensity_embed()
        current_time = datetime.now().timestamp()
        if not self.map_url or current_time - self._last_update >= self._map_update_interval:
            eq = self.eew.earthquake
            if not eq.map._drawn:
                intensity_embed.remove_image()
                file = {}
            else:
                eq.map.draw_wave(current_time - eq.time.timestamp() + self.get_latency())
                file = {"file": discord.File(eq.map.save(), "image.png")}

            self._last_update = datetime.now().timestamp()
            self._map_update_interval = max(self._last_update - current_time, self._map_update_interval)

            m = await self._edit_singal_message(self.messages[0], intensity_embed, **file)
            if len(m.embeds) > 1 and (image := m.embeds[1].image):
                self.map_url = image.url
            elif self.eew.earthquake.map.image is not None:
                # if intensity calc has done but map not drawn
                self.bot.logger.warning("Failed to get image url.")

            update = ()
            intensity_embed = self.intensity_embed()
        else:
            update = (self._edit_singal_message(self.messages[0], intensity_embed.copy()),)
        intensity_embed.set_image(url=self.map_url)

        await asyncio.gather(
            *update,
            *(self._edit_singal_message(msg, intensity_embed) for msg in self.messages[1:]),
            return_exceptions=True,
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

        return self

    async def lift_eew(self):
        """
        Lift the EEW alert.
        """
        self._info_embed.title = f"地震速報（共 {self.eew.serial} 報）播報結束"
        original_intensity_embed = self._intensity_embed.copy().set_image(url="attachment://image.png")

        await asyncio.gather(
            self._edit_singal_message(self.messages[0], original_intensity_embed),
            *(self._edit_singal_message(msg, self._intensity_embed) for msg in self.messages[1:]),
            return_exceptions=True,
        )
        self.bot.load_extensions


class DiscordNotification(BaseNotificationClient, discord.Bot):
    """
    Represents a discord notification client.
    """

    # eew-id: EEWMessages
    alerts: dict[str, EEWMessages] = {}
    notification_channels: list[NotifyAndChannel] = []

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

        for data in self.config["channels"]:
            channel = await self.get_or_fetch_channel(data["id"], None)
            if channel is None:
                self.logger.warning(f"Ignore channel '{data['id']}' because it was not found.")
                continue
            elif not isinstance(channel, discord.TextChannel):
                self.logger.warning(f"Ignore channel '{channel.id}' because it is not a text channel.")
                continue
            mention = (
                None
                if not (m := data.get("mention"))
                else (f"<@&{m}>" if isinstance(m, int) else f"@{m.removeprefix('@')}")
            )
            self.notification_channels.append({"channel": channel, "mention": mention})

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

    async def send_eew(self, eew: EEW) -> Optional[EEWMessages]:
        if len(self.notification_channels) == 0:
            self.logger.warning("No Discord notification channel available.")
            return None

        m = await EEWMessages.send(self, eew, self.notification_channels)
        if m is None:
            self.logger.warning("Failed to send EEW message.")
            return None
        self.alerts[eew.id] = m

        if not self.update_eew_messages_loop.is_running():
            self.update_eew_messages_loop.start()

        return m

    async def update_eew(self, eew: EEW) -> Optional[EEWMessages]:
        m = self.alerts.get(eew.id)
        if m is None:
            return await self.send_eew(eew)

        return await m.update_eew_data(eew)

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
                await self.lift_eew(m.eew)
            else:
                await m.edit()


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

    return DiscordNotification(logger, config, token)
