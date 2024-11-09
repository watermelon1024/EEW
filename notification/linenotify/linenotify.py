import asyncio
from datetime import datetime

import aiohttp

from src import EEW, BaseNotificationClient, Config, Logger

LINE_NOTIFY_API = "https://notify-api.line.me/api/notify"


class LineNotifyClient(BaseNotificationClient):
    """
    Represents a [custom] EEW notification client.
    """

    def __init__(self, logger: Logger, config: Config, notify_token: str) -> None:
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
        logger.warning(
            "LINE Notify will end its services on 2025/04/01. "
            "See also: https://notify-bot.line.me/closing-announce"
        )

    def get_eew_message(self, eew: EEW):
        # 取得EEW訊息並排版
        eq = eew.earthquake
        time_str = eq.time.strftime("%m月%d日 %H:%M:%S")
        content = (
            f"\n{time_str},\n發生規模 {eq.mag} 地震,\n編號{eew.id},"
            f"\n震央位在{eq.location.display_name or eq.location},"
            f"\n震源深度{eq.depth} 公里,\n最大震度{eq.max_intensity.display}"
        )
        provider = f"\n(發報單位: {eew.provider.display_name})"
        _message = f"{content} {provider}"
        return _message

    async def get_region_intensity(self, eew: EEW):
        # 取得各地震度和抵達時間
        eq = eew.earthquake
        intensity_dict: dict[tuple[str, str], tuple[str, int]] = {}

        for city, intensity in eq.city_max_intensity.items():
            if intensity.intensity.value > 0:
                key = (city, intensity.region.name)
                intensity_dict[key] = (
                    intensity.intensity.display,
                    int(intensity.distance.s_arrival_time.timestamp()),
                )

        return intensity_dict

    async def _send_region_intensity(self, eew: EEW):
        # 發送各地震度和抵達時間並排版
        eq = eew.earthquake
        await eq._intensity_calculated.wait()
        if eq._intensity_calculated.is_set():
            region_intensity = await self.get_region_intensity(eew)
            current_time = int(datetime.now().timestamp())
            region_intensity_message = f"\n🚨第{eew.serial}報🚨\n⚠️以下僅供參考⚠️\n預估震度|抵達時間:"

            for (city, region), (intensity, s_arrival_time) in region_intensity.items():
                arrival_time = max(s_arrival_time - current_time, 0)
                region_intensity_message += f"\n{city} {region}:{intensity}\n剩餘{arrival_time}秒抵達"

            region_intensity_message += "\n⚠️請以氣象署為準⚠️"

            _headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self._notify_token}",
            }
            async with aiohttp.ClientSession(headers=_headers) as session:
                await self._post_line_api(session, intensity_msg=region_intensity_message)

            asyncio.create_task(self._send_eew_img(eew))

    async def _send_eew_img(self, eew: EEW):
        # 發送各地震度圖片
        eq = eew.earthquake
        try:
            message = self.get_eew_message(eew)
            img_msg = f"\n⚠️圖片僅供參考⚠️\n⚠️以氣象署為準⚠️"
            await eq._calc_task
            if eq.map._drawn:
                message += img_msg
                image = eq.map.save().getvalue()
                __headers = {"Authorization": f"Bearer {self._notify_token}"}
                async with aiohttp.ClientSession(headers=__headers) as session:
                    await self._post_line_api(session, msg=message, img=image)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.exception(f"Failed to send image alert to Line-Notify: {e}")

    async def _post_line_api(
        self, session: aiohttp.ClientSession, img=None, msg: str = None, intensity_msg: str = None
    ) -> None:
        try:
            # 確認img是否有和其他msg一組
            if img and not msg and not intensity_msg:
                raise ValueError("Image provided without a message.")

            form = aiohttp.FormData()
            if msg:
                form.add_field("message", msg)
            elif intensity_msg:
                form.add_field("message", intensity_msg)
            if img:
                form.add_field("imageFile", img)

            async with session.post(url=LINE_NOTIFY_API, data=form) as response:
                if response.ok:
                    self.logger.info(f"Message sent to Line-Notify successfully")

                else:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        status=response.status,
                        history=response.history,
                        message=await response.text(),
                    )
        except ValueError as e:
            self.logger.error(f"ValueError: {e}")
        except Exception as e:
            self.logger.exception(f"Failed to send message alert to Line-Notify: {e}")

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

        await self._send_region_intensity(eew)

    async def update_eew(self, eew: EEW):
        """
        If an EEW is updated, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The updated EEW.
        :type eew: EEW
        """
        await self._send_region_intensity(eew)
