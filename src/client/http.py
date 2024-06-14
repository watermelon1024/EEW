import asyncio
import random
import time

import aiohttp

from ..earthquake.eew import EEW
from ..utils import MISSING
from .abc import EEWClient

DOMAIN = "exptech.dev"
API_NODES = [f"https://api-{i}.{DOMAIN}" for i in range(1, 3)]


async def _check_latency(session: aiohttp.ClientSession, node: str):
    try:
        start = time.time()
        async with session.get(f"{node}/eq/eew") as response:
            if 200 <= response.status < 300:
                latency = time.time() - start
                return node, latency
            else:
                return node, float("inf")
    except Exception:
        return node, float("inf")


class HTTPEEWClient(EEWClient):
    """
    Represents a HTTP EEW API Client.
    """

    __session: aiohttp.ClientSession = MISSING
    __task: asyncio.Task = MISSING
    __event_loop: asyncio.AbstractEventLoop = MISSING
    _alerts: dict[str, EEW] = {}
    node_latencies: list[tuple[str, float]] = []
    _current_node_index: int = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def recreate_session(self):
        if not self.__session or self.__session.closed:
            self.__session = aiohttp.ClientSession()

    async def new_alert(self, data: dict):
        eew = EEW.from_dict(data)
        self._alerts[eew.id] = eew

        self.logger.info(
            "New EEW alert is detected!\n"
            "--------------------------------\n"
            f"       ID: {eew.id} (Serial {eew.serial})\n"
            f" Location: {eew.earthquake.location.display_name}({eew.earthquake.lon}, {eew.earthquake.lat})\n"
            f"Magnitude: {eew.earthquake.mag}\n"
            f"    Depth: {eew.earthquake.depth}km\n"
            f"     Time: {eew.earthquake.time.strftime('%Y/%m/%d %H:%M:%S')}\n"
            "--------------------------------"
        )

        eew.earthquake.calc_all_data_in_executor(self.__event_loop)

        # call custom notification client
        await asyncio.gather(*(c.send_eew(eew) for c in self._notification_client), return_exceptions=True)

        return eew

    async def update_alert(self, data: dict):
        eew = EEW.from_dict(data)
        old_eew = self._alerts.get(eew.id)
        self._alerts[eew.id] = eew

        self.logger.info(
            "EEW alert updated\n"
            "--------------------------------\n"
            f"       ID: {eew.id} (Serial {eew.serial})\n"
            f" Location: {eew.earthquake.location.display_name}({eew.earthquake.lon:.2f}, {eew.earthquake.lat:.2f})\n"
            f"Magnitude: {eew.earthquake.mag}\n"
            f"    Depth: {eew.earthquake.depth}km\n"
            f"     Time: {eew.earthquake.time.strftime('%Y/%m/%d %H:%M:%S')}\n"
            "--------------------------------"
        )

        if old_eew is not None:
            old_eew.earthquake._calc_task.cancel()
        eew.earthquake.calc_all_data_in_executor(self.__event_loop)

        # call custom notification client
        await asyncio.gather(*(c.update_eew(eew) for c in self._notification_client), return_exceptions=True)

        return eew

    async def lift_alert(self, eew: EEW):
        # call custom notification client
        await asyncio.gather(*(c.lift_eew(eew) for c in self._notification_client), return_exceptions=True)

    def switch_api_node(self, type: str = "next"):
        """
        Switch to the API node.

        :param type: The type of the API node, supports `next`, `fastest` and `random`.
        :type type: str
        """
        if type == "next":
            self._current_node_index = (self._current_node_index + 1) % len(self.node_latencies)
            self.BASE_URL = self.node_latencies[self._current_node_index][0]
        elif type == "fastest":
            self.BASE_URL = self.node_latencies[0][0]
        elif type == "random":
            self.BASE_URL = random.choice(self.node_latencies)[0]
        else:
            raise ValueError(f"Invalid type: {type}")
        self.logger.info(f"Switched to API node: {self.BASE_URL}")

    async def _get_request(self, retry: int = 0):
        try:
            async with self.__session.get(f"{self.BASE_URL}/eq/eew?type=cwa") as r:
                data: list[dict] = await r.json()
                if not data:
                    return
        except Exception as e:
            if retry > 0:
                self.recreate_session()
                self.switch_api_node()
                await asyncio.sleep(1)
                return await self._get_request(retry - 1)
            self.logger.exception("Fail to get eew data.", exc_info=e)
            return

        _check_finished_alerts = set(self._alerts.keys())
        for d in data:
            id = d["id"]
            _check_finished_alerts.discard(id)
            cached_eew = self._alerts.get(id)
            if cached_eew is None:
                await self.new_alert(d)
            elif d["serial"] > cached_eew.serial:
                await self.update_alert(d)

        # remove finished alerts
        for id in _check_finished_alerts:
            cached_eew = self._alerts.pop(id, None)
            if cached_eew is not None:
                await self.lift_alert(cached_eew)

    async def _loop(self):
        self.__event_loop = asyncio.get_event_loop()
        self.logger.info("EEW Client is ready.")
        while True:
            if not self.__task or self.__task.done():
                self.__task = self.__event_loop.create_task(self._get_request(3))

            await asyncio.sleep(0.5)

    async def start(self):
        """
        Start the client.
        Note: This coro won't finish forever until user interrupt it.
        """
        self.recreate_session()
        self.run_notification_client()
        # get the fastest node
        latencies = await asyncio.gather(
            *(_check_latency(self.__session, f"{url}/api/v{self._API_VERSION}") for url in API_NODES)
        )
        self.node_latencies = sorted(latencies, key=lambda x: (x[1], x[0]))
        self.BASE_URL = self.node_latencies[0][0]
        self.logger.debug(f"API node latencies: {self.node_latencies}")
        self.logger.info(f"Using fastest API node: {self.BASE_URL}")
        await self._loop()

    def run(self):
        """
        Start the client.
        Note: This is a blocking call. If you want to control your own event loop, use `start` instead.
        """
        self.logger.info("Starting EEW Client...")
        self.__event_loop = asyncio.get_event_loop()
        self.__event_loop.create_task(self.start())
        try:
            self.__event_loop.run_forever()
        except KeyboardInterrupt:
            self.__event_loop.stop()
        finally:
            self.logger.info("EEW Client has been stopped.")
