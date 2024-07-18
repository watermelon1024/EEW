import asyncio
import math
from datetime import datetime
from typing import TYPE_CHECKING, Optional, TypedDict

import discord

from src import EEW

if TYPE_CHECKING:
    from .bot import DiscordNotification


class NotificationChannel(TypedDict):
    channel: discord.TextChannel
    mention: Optional[str]


class _SingleMessage:
    """
    Represents a single message.
    """

    __slots__ = ("message", "mention", "edit")

    def __init__(self, message: discord.Message, mention: Optional[str]) -> None:
        self.message = message
        self.mention = mention

        self.edit = self.message.edit


class EEWMessages:
    """
    Represents discord messages with EEW data.
    """

    __slots__ = (
        "bot",
        "eew",
        "messages",
        "__ready",
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
        :param messages: The discord message.
        :type messages: list[_SingleMessage]
        """
        self.bot = bot
        self.eew = eew
        self.messages = messages
        self.__ready = asyncio.Event()

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

    async def _send_first_message(self):
        "Fisrt time send message(s) in discord"
        eq = self.eew.earthquake
        msg = f"{eq.time.strftime('%H:%M:%S')} 於 {eq.location.display_name or eq.location} 發生規模 {eq.mag} 有感地震，慎防搖晃！"
        self.messages = list(
            filter(
                None,
                await asyncio.gather(
                    *(
                        self._send_single_message(channel["channel"], msg, channel["mention"])
                        for channel in self.bot.notification_channels
                    )
                ),
            )
        )
        self.__ready.set()

    async def _send_single_message(
        self, channel: discord.TextChannel, content: str, mention: Optional[str] = None
    ):
        try:
            return _SingleMessage(await channel.send(f"{content} {mention or ''}"), mention)
        except Exception as e:
            self.bot.logger.exception(f"Failed to send message in {channel.name}", exc_info=e)
            return None

    async def _edit_single_message(self, message: _SingleMessage, intensity_embed: discord.Embed, **kwargs):
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
    ) -> Optional["EEWMessages"]:
        """
        Send new discord messages.

        :param bot: The discord bot.
        :type bot: DiscordNotification
        :param eew: The EEW instance.
        :type eew: EEW
        :return: The new discord messages.
        :rtype: EEWMessage
        """
        self = cls(bot, eew, [])
        bot.loop.create_task(self._send_first_message())

        self._info_embed = self.info_embed()
        self._intensity_embed = discord.Embed(title="震度等級預估", description="計算中...")
        return self

    async def edit(self) -> None:
        """
        Edit the discord messages to update S wave arrival time.
        """
        intensity_embed = self.intensity_embed()
        current_time = datetime.now().timestamp()
        await self.__ready.wait()  # wait for all messages sent successfully
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

            m = await self._edit_single_message(self.messages[0], intensity_embed, **file)
            if len(m.embeds) > 1 and (image := m.embeds[1].image):
                self.map_url = image.url
            elif self.eew.earthquake.map.image is not None:
                # if intensity calc has done but map not drawn
                self.bot.logger.warning("Failed to get image url.")

            update = ()
            intensity_embed = self.intensity_embed()
        else:
            update = (self._edit_single_message(self.messages[0], intensity_embed.copy()),)
        intensity_embed.set_image(url=self.map_url)

        await asyncio.gather(
            *update,
            *(self._edit_single_message(msg, intensity_embed) for msg in self.messages[1:]),
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
            self._edit_single_message(self.messages[0], original_intensity_embed),
            *(self._edit_single_message(msg, self._intensity_embed) for msg in self.messages[1:]),
            return_exceptions=True,
        )
