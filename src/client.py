import asyncio

import aiohttp

from .config import Config
from .earthquake.eew import EEW
from .earthquake.location import RegionLocation
from .logging import Logger
from .notify.abc import NotificationClient
from .utils import MISSING


class EEWClient:
    """
    Represents a base EEW API Client.
    """

    def __init__(
        self,
        config: Config,
        logger: Logger,
        alert_regions: list[RegionLocation] = MISSING,
        calculate_site_effect: bool = False,
        notification_client: list[NotificationClient] = MISSING,
        api_version: int = 1,
    ) -> None:
        self.config = config
        self.debug_mode: bool = config["debug-mode"]
        self.logger = logger

        self._alert_regions = alert_regions
        self._calc_site_effect = calculate_site_effect
        self._notification_client = notification_client or []

        self.__API_VERSION = api_version
        self.BASE_URL = f"https://api-2.exptech.com.tw/api/v{api_version}"

    def add_notification(self, client: NotificationClient):
        """
        Add a notification client.
        """
        self._notification_client.append(client)

    def run_notification_client(self, loop: asyncio.AbstractEventLoop):
        """
        Run the notification client.
        """
        return [client.run() for client in self._notification_client]


class HTTPEEWClient(EEWClient):
    """
    Represents a HTTP EEW API Client.
    """

    __session: aiohttp.ClientSession = MISSING
    __task: asyncio.Task = MISSING
    __event_loop: asyncio.AbstractEventLoop = MISSING
    _alerts: dict[str, EEW] = {}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger.info("EEW Client is ready.")

    def recreate_session(self):
        if not self.__session or self.__session.closed:
            self.__session = aiohttp.ClientSession()

    async def new_alert(self, data: dict):
        eew = EEW.from_dict(data)
        self._alerts[eew.id] = eew

        # call custom notification client
        for client in self._notification_client:
            await client.send_eew(eew)

        return eew

    async def update_alert(self, data: dict):
        eew = EEW.from_dict(data)
        self._alerts[eew.id] = eew

        # call custom notification client
        for client in self._notification_client:
            await client.update_eew(eew)

        return eew

    async def lift_alert(self, eew: EEW):
        # call custom notification client
        for client in self._notification_client:
            await client.lift_eew(eew)

    async def _get_request(self, retry: int = 0):
        try:
            async with self.__session.get(f"{self.BASE_URL}/eq/eew?type=cwa") as r:
                data: list[dict] = await r.json()
                if not data:
                    return
        except Exception as e:
            if retry > 0:
                self.recreate_session()
                return await self._get_request(retry - 1)
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
            eew = self._alerts.pop(id, None)
            if eew is not None:
                self.lift_alert(eew)

    async def _loop(self):
        self.__event_loop = asyncio.get_event_loop()
        while True:
            if not self.__task or self.__task.done():
                self.__task = self.__event_loop.create_task(self._get_request())

            await asyncio.sleep(1)

    async def start(self):
        """
        Start the client.
        Note: This coro won't finish forever until user interrupt it.
        """
        self.recreate_session()
        await asyncio.gather(*self.run_notification_client(self.__event_loop), self._loop())

    def run(self):
        """
        Start the client.
        Note: This is a blocking call. If you want to control your own event loop, use `start` instead.
        """
        asyncio.run(self.start())
