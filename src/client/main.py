import asyncio
import logging

import aiohttp

from ..config import Config
from ..earthquake.eew import EEW
from ..earthquake.location import RegionLocation
from ..logging import InterceptHandler, Logging
from ..notify.base import NotificationClient
from ..utils import MISSING


class EEWClient:
    """
    Represents a base EEW API Client.
    """

    def __init__(
        self,
        alert_regions: list[RegionLocation] = MISSING,
        calculate_site_effect: bool = False,
        notify_client: list[NotificationClient] = MISSING,
        api_version: int = 1,
    ) -> None:
        self._alert_regions = alert_regions
        self._calc_site_effect = calculate_site_effect
        self._notify_client = notify_client

        self.__API_VERSION = api_version
        self.BASE_URL = f"https://api-2.exptech.com.tw/api/v{api_version}"

        self.config = Config()
        self.debug_mode: bool = self.config["debug-mode"]
        self.logger = Logging(
            retention=self.config["log"]["retention"],
            debug_mode=self.debug_mode,
            format=self.config["log"]["format"],
        ).get_logger()
        logging.basicConfig(
            handlers=[InterceptHandler(self.logger)],
            level=0 if self.debug_mode else logging.INFO,
            force=True,
        )


class HTTPEEWClient(EEWClient):
    """
    Represents a HTTP EEW API Client.
    """

    __session: aiohttp.ClientSession = MISSING
    __task: asyncio.Task = MISSING
    _alerts: dict[str, EEW] = {}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.recreate_session()
        self._event_loop = asyncio.get_event_loop()

    def recreate_session(self):
        if not self.__session or self.__session.closed:
            self.__session = aiohttp.ClientSession()

    async def new_alert(self, data: dict):
        eew = EEW.from_dict(data)
        self._alerts[eew.id] = eew

        # call custom notify client
        for client in self._notify_client:
            await client.send_eew(eew)

        return eew

    async def update_alert(self, data: dict):
        eew = EEW.from_dict(data)
        self._alerts[eew.id] = eew

        # call custom notify client
        for client in self._notify_client:
            await client.update_eew(eew)

        return eew

    async def _get_request(self):
        async with self.__session.get(f"{self.BASE_URL}/eq/eew") as r:
            try:
                data: list[dict] = await r.json()
                if not data:
                    return
            except Exception as e:
                self.logger.exception("Fail to get eew data.", exc_info=e)
                return

        _check_finished_alerts = set(self._alerts.keys())
        for d in data:
            id = d["id"]
            _check_finished_alerts.discard(id)
            eew = self._alerts.get(id)
            if eew is None:
                await self.new_alert(d)
            elif eew.serial != d["serial"]:
                await self.update_alert(d)

        # remove finished alerts
        for id in _check_finished_alerts:
            self._alerts.pop(id, None)

    async def _loop(self):
        while True:
            if not self.__task or self.__task.done():
                self.__task = self._event_loop.create_task(self._get_request())
            await asyncio.sleep(1)
