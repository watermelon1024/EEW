import asyncio
from datetime import datetime
from typing import Optional

import aiohttp

from src import EEW, BaseNotificationClient, Config, Logger

LINE_NOTIFY_API = "https://notify-api.line.me/api/notify"


class LineNotifyClient(BaseNotificationClient):
    """
    Represents a [custom] EEW notification client.
    """

    def __init__(self, logger: Logger, config: Config,
                 notify_token: str) -> None:
        """
        Initialize a new [custom] notification client.

        :param logger: The logger instance.
        :type logger: Logger
        :param config: The configuration.
        :type config: Config
        :param notify_token: The LINE Notify API token.
        :type notify_token: str
        """
        self.logger = logger
        self.config = config
        self._notify_token = notify_token
        self.response_status: int = None
        self._region_intensity: Optional[dict[tuple[str, str],
                                              tuple[str, int]]] = None

    def get_eew_message(self, eew: EEW):
        #取得EEW訊息並排版
        eq = eew.earthquake
        time_str = eq.time.strftime("%H:%M:%S")
        i = {eew.serial} - 1
        title = f"\n速報更新{i}"
        content = (
            f"\n{time_str} 於 {eq.location.display_name or eq.location},\n發生規模 {eq.mag} 地震,"
            f"\n震源深度{eq.depth} 公里,\n最大震度{eq.max_intensity.display},"
            "\n慎防強烈搖晃，就近避難 趴下、掩護、穩住!")
        provider = f"\n(發報單位: {eew.provider.display_name})"
        if eew.serial > 1:
            _message = f"{title} {content} {provider}"
        else:
            _message = f"{content} {provider}"

        return _message

    def get_region_intensity(self, eew: EEW):
        #取得各地震度和抵達時間
        self._region_intensity = {
            (city, intensity.region.name): (
                intensity.intensity.display,
                int(intensity.distance.s_arrival_time.timestamp()),
            )
            for city, intensity in eew.earthquake.city_max_intensity.items()
            if intensity.intensity.value > 0
        }

        return self._region_intensity

    async def _send_region_intensity(self, eew: EEW):
        #發送各地震度和抵達時間並排版
        eq = eew.earthquake
        await eq._intensity_calculated.wait()
        if eq._intensity_calculated.is_set():
            self.get_region_intensity(eew)
        if self._region_intensity is not None:
            current_time = int(datetime.now().timestamp())
            if eew.serial <= 1:
                region_intensity_message = "\n以下僅供參考\n實際以氣象署公布為準\n各地最大震度|抵達時間:"
                for (city, region), (
                        intensity,
                        s_arrival_time) in self._region_intensity.items():
                    arrival_time = max(s_arrival_time - current_time, 0)
                    region_intensity_message += f"\n{city} {region}:{intensity}\n剩餘{arrival_time}秒抵達"
            else:
                region_intensity_message = "\n以下僅供參考\n實際以氣象署公布為準\n各地最大震度更新:"
                for (city, region), (
                        intensity,
                        s_arrival_time) in self._region_intensity.items():
                    region_intensity_message += f"\n{city} {region}:{intensity}"

            _headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self._notify_token}"
            }
            async with aiohttp.ClientSession(headers=_headers) as session:
                await self._send_message(
                    session, region_intensity_message=region_intensity_message)

    async def _send_image(self, eew: EEW):
        #發送各地震度圖片
        eq = eew.earthquake
        try:
            await eq._calc_task
            if eq.map._drawn:
                image = eq.map.save().getvalue()
                __headers = {"Authorization": f"Bearer {self._notify_token}"}
                async with aiohttp.ClientSession(headers=__headers) as session:
                    await self._send_message(session, image=image)

        except asyncio.CancelledError:
            pass

    async def _send_message(self,
                            session: aiohttp.ClientSession,
                            image=None,
                            message: str = None,
                            region_intensity_message: str = None) -> None:
        try:
            form = aiohttp.FormData()
            if message:
                form.add_field('message', message)
            elif region_intensity_message:
                form.add_field('message', region_intensity_message)
            if image:
                form.add_field('message', "\n各地震度(僅供參考)\n以氣象署公布為準")
                form.add_field('imageFile', image)

            async with session.post(url=LINE_NOTIFY_API,
                                    data=form) as response:
                if not response.ok:
                    raise aiohttp.ClientResponseError(response.request_info,
                                                      status=response.status,
                                                      history=response.history,
                                                      message=await
                                                      response.text())
                else:
                    self.response_status = response.status
                    self.logger.info(
                        "Message sent to Line-Notify successfully")
        except Exception as e:
            self.logger.exception(
                f"Failed to send message alert to Line-Notify: {e}")

    async def start(self) -> None:
        """
        The entrypoint for the notification client.
        If this client doesn't need to run in the event loop, just type `pass` because this method is required.

        Note: DO NOT do any blocking calls to run the otification client.
        """
        self.logger.info("LINE Notify is ready")

    async def send_eew(self, eew: EEW):
        """
        If an new EEW is detected, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The EEW.
        :type eew: EEW
        """

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {self._notify_token}"
        }
        message = self.get_eew_message(eew)
        async with aiohttp.ClientSession(headers=headers) as session:
            await self._send_message(session, message=message)

        await self._send_region_intensity(eew)
        asyncio.create_task(self._send_image(eew))

    async def update_eew(self, eew: EEW):
        """
        If an EEW is updated, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The updated EEW.
        :type eew: EEW
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {self._notify_token}"
        }
        message = self.get_eew_message(eew)
        async with aiohttp.ClientSession(headers=headers) as session:
            await self._send_message(session, message=message)

        await self._send_region_intensity(eew)
        asyncio.create_task(self._send_image(eew))
