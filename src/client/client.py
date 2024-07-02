import asyncio
from collections import defaultdict
from typing import Any, Optional

import aiohttp
from cachetools import TTLCache

from ..earthquake.eew import EEW
from ..logging import Logger
from ..notification.base import NotificationClient
from .http import HTTPClient
from .websocket import (
    AuthorizationFailed,
    ExpTechWebSocket,
    WebSocketConnectionConfig,
    WebSocketEvent,
    WebSocketReconnect,
)


class Client:
    logger: Logger
    debug_mode: bool
    alerts: TTLCache[str, EEW]
    notification_client: list[NotificationClient]
    _loop: Optional[asyncio.AbstractEventLoop]
    _http: HTTPClient
    _ws: Optional[ExpTechWebSocket]
    websocket_config: WebSocketConnectionConfig
    event_handlers: defaultdict[list]
    __ready: asyncio.Event
    _reconnect = True
    __closed = False

    def __init__(
        self,
        logger: Logger,
        websocket_config: WebSocketConnectionConfig = None,
        debug: bool = False,
        session: aiohttp.ClientSession = None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        self.logger = logger
        self.debug_mode = debug
        self._loop = loop or asyncio.get_event_loop()
        self._http = HTTPClient(logger, debug, session=session, loop=self._loop)
        self._ws = None
        self.websocket_config = websocket_config

        self.alerts = TTLCache(maxsize=float("inf"), ttl=60 * 60)  # 1hr
        self.notification_client = []
        self.event_handlers = defaultdict(list)
        self.__ready = asyncio.Event()

    async def new_alert(self, data: dict):
        eew = EEW.from_dict(data)
        self.alerts[eew.id] = eew

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

        eew.earthquake.calc_all_data_in_executor(self._loop)

        # call custom notification client
        for client in self.notification_client:
            self._loop.create_task(client.send_eew(eew))

    async def update_alert(self, data: dict):
        eew = EEW.from_dict(data)
        old_eew = self.alerts.get(eew.id)
        self.alerts[eew.id] = eew

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
        eew.earthquake.calc_all_data_in_executor(self._loop)

        # call custom notification client
        for client in self.notification_client:
            self._loop.create_task(client.update_eew(eew))

    async def _emit(self, event: str, *args):
        for handler in self.event_handlers[event]:
            self._loop.create_task(handler(*args))

    def add_listener(self, event: WebSocketEvent, handler: Any):
        self.event_handlers[event].append(handler)
        return self

    async def on_eew(self, data: dict):
        if data["author"] != "cwa":
            # now only receive caw's eew
            # TODO: support other source's eew
            return
        eew = self.alerts.get(data["id"])
        if eew is None:
            await self.new_alert(data)
        elif data["serial"] > eew.serial:
            await self.update_alert(data)

    async def connect(self):
        """Connect to ExpTech API and start receiving data"""
        if self.websocket_config:
            self._http.test_ws_latencies()
            self._http.switch_ws_node("fastest")
            await self.ws_connect()
        else:
            await self._get_eew_loop()

    async def ws_connect(self):
        """Connect to WebSocket"""

        in_reconnect = False
        task: asyncio.Task = None
        while not self.__closed:
            try:
                if not self._ws or self._ws.closed:
                    self.logger.debug("Connecting to WebSocket...")
                    self._ws = await self._http.ws_connect(self)
                if not self.__ready.is_set():
                    self.logger.info(
                        "ExpTech WebSocket is ready\n"
                        "--------------------------------------------------\n"
                        f"Subscribed services: {', '.join(self._ws.subscribed_services)}\n"
                        "--------------------------------------------------"
                    )
                    self.__ready.set()
                elif in_reconnect:
                    self.logger.info(
                        "ExpTech WebSocket successfully reconnect\n"
                        "--------------------------------------------------\n"
                        f"Subscribed services: {', '.join(self._ws.subscribed_services)}\n"
                        "--------------------------------------------------"
                    )
                if task:
                    task.cancel()
                in_reconnect = False
                self._reconnect_delay = 0
                while True:
                    await self._ws.pool_event()
            except AuthorizationFailed:
                await self.close()
                self.logger.warning("Authorization failed, switching to HTTP client")
                self.websocket_config = None
                await self.connect()
                return
            except WebSocketReconnect as e:
                if e.reopen and self._ws and not self._ws.closed:
                    await self._ws.close()
                in_reconnect = True
                self._reconnect_delay += 10
                self.logger.exception(f"Attempting a reconnect in {self._reconnect_delay}s: {e.reason}")
            except Exception as e:
                self._reconnect_delay += 10
                self.logger.exception(
                    f"An unhandleable error occurred, reconnecting in {self._reconnect_delay}s", exc_info=e
                )
            # use http client while reconnecting
            task = self._loop.create_task(self._get_eew_loop())
            await asyncio.sleep(self._reconnect_delay)
            self._http.switch_ws_node()

    async def get_eew(self):
        try:
            data: list[dict] = await self._http.get("/eq/eew")
        except Exception as e:
            self.logger.exception("Fail to get eew data.", exc_info=e)
            return

        for d in data:
            id = d["id"]
            cached_eew = self.alerts.get(id)
            if cached_eew is None:
                await self.new_alert(d)
            elif d["serial"] > cached_eew.serial:
                await self.update_alert(d)

        self.alerts.expire()

    async def _get_eew_loop(self):
        self.logger.info("Starting ExpTech HTTP client is ready")
        self.__ready.set()
        task: asyncio.Task = None
        while True:
            try:
                if not task or task.done():
                    task = self._loop.create_task(self.get_eew())
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return

    async def close(self):
        """Close the websocket"""
        self._reconnect = False
        self.__closed = True
        if self._ws:
            await self._ws.close()

    def closed(self):
        """Whether the websocket is closed"""
        return self.__closed

    async def start(self):
        """
        Start the client.
        Note: This coro won't finish forever until user interrupt it.
        """
        self.logger.info("Starting ExpTech API Client...")

        # test latencies
        self._http.test_api_latencies()
        self._http.switch_api_node("fastest")

        self.add_listener(WebSocketEvent.EEW.value, self.on_eew)
        for client in self.notification_client:
            self._loop.create_task(client.run())
            # TODO: wait until notification client ready

        await self.connect()

    def run(self):
        """
        Start the client.
        Note: This is a blocking call. If you want to control your own event loop, use `start` instead.
        """
        try:
            self._loop.create_task(self.start())
            self._loop.run_forever()
        except KeyboardInterrupt:
            self._loop.run_until_complete(self.close())
            self._loop.stop()
        finally:
            self.logger.info("ExpTech API client has been stopped.")

    async def wait_until_ready(self):
        """Wait until the client is ready"""
        await self.__ready.wait()
