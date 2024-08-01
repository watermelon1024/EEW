import asyncio
import importlib
import os
import re
from collections import defaultdict
from typing import Any, Optional

import aiohttp
from cachetools import TTLCache

from ..config import Config
from ..earthquake.eew import EEW
from ..logging import Logger
from ..notification.base import BaseNotificationClient
from .http import HTTPClient
from .websocket import (
    AuthorizationFailed,
    ExpTechWebSocket,
    WebSocketConnectionConfig,
    WebSocketEvent,
    WebSocketReconnect,
)


class Client:
    """A client for interacting with ExpTech API."""

    config: Config
    logger: Logger
    debug_mode: bool
    __eew_source: Optional[list[str]]
    alerts: TTLCache[str, EEW]
    notification_client: list[BaseNotificationClient]
    _loop: Optional[asyncio.AbstractEventLoop]
    _http: HTTPClient
    _ws: Optional[ExpTechWebSocket]
    websocket_config: WebSocketConnectionConfig
    event_handlers: defaultdict[str, list]
    __ready: asyncio.Event
    _reconnect = True
    __closed = False

    def __init__(
        self,
        config: Config,
        logger: Logger,
        websocket_config: WebSocketConnectionConfig = None,
        debug: bool = False,
        session: aiohttp.ClientSession = None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        self.config = config
        self.logger = logger
        self.debug_mode = debug
        self._loop = loop or asyncio.get_event_loop()
        self._http = HTTPClient(logger, debug, session=session, loop=self._loop)
        self._ws = None
        self.websocket_config = websocket_config

        self.alerts = TTLCache(maxsize=float("inf"), ttl=60 * 60)  # 1hr
        eew_source: dict = config.get("eew_source")
        self.__eew_source = (
            None if eew_source.get("all") else [source for source, enable in eew_source.items() if enable]
        )
        self.notification_client = []
        self.event_handlers = defaultdict(list)
        self.__ready = asyncio.Event()

    async def new_alert(self, data: dict):
        """Send a new EEW alert"""
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
        """Update an existing EEW alert"""
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
        """Add a listener for a specific event"""
        self.event_handlers[event].append(handler)
        return self

    async def on_eew(self, data: dict):
        """Handle EEW event"""
        if self.__eew_source is not None and data["author"] not in self.__eew_source:
            # source is None: all source
            # source is list: only specified source
            return

        self.alerts.expire()
        eew = self.alerts.get(data["id"])
        if eew is None:
            await self.new_alert(data)
        elif data["serial"] > eew.serial:
            await self.update_alert(data)

    async def connect(self):
        """Connect to ExpTech API and start receiving data"""
        if self.websocket_config:
            # await self._http.test_ws_latencies()
            # self._http.switch_ws_node("fastest")
            await self.ws_connect()
        else:
            await self._get_eew_loop()

    async def ws_connect(self):
        """Connect to WebSocket"""
        in_reconnect = False
        _reconnect_delay = 0
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
                _reconnect_delay = 0
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
                self.logger.exception(f"Attempting a reconnect in {_reconnect_delay}s: {e.reason}")
            except Exception as e:
                self.logger.exception(
                    f"An unhandleable error occurred, reconnecting in {_reconnect_delay}s", exc_info=e
                )
            # use http client while reconnecting
            if not task or task.done():
                task = self._loop.create_task(self._get_eew_loop())
            in_reconnect = True
            if _reconnect_delay < 600:  # max reconnect delay 10min
                _reconnect_delay += 10
            await asyncio.sleep(_reconnect_delay)
            self._http.switch_ws_node()

    async def get_eew(self):
        try:
            data: list[dict] = await self._http.get("/eq/eew")
        except Exception as e:
            self.logger.exception("Fail to get eew data.", exc_info=e)
            return

        for d in data:
            await self.on_eew(d)

    async def _get_eew_loop(self):
        self.logger.info("ExpTech HTTP client is ready")
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
        # await self._http.test_api_latencies()
        # self._http.switch_api_node("fastest")

        self.add_listener(WebSocketEvent.EEW.value, self.on_eew)
        for client in self.notification_client:
            self._loop.create_task(client.start())
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
        """Wait until the API client is ready"""
        await self.__ready.wait()

    def load_notification_client(self, path: str, is_module: bool = False):
        """Load a notification client"""
        module_path = path + (".register" if is_module else "")
        module_name = path.split(".")[-1]

        try:
            self.logger.debug(f"Importing {module_path}...")
            module = importlib.import_module(module_path)
            register_func = getattr(module, "register", None)
            if register_func is None:
                self.logger.debug(
                    f"Ignoring registering {module_name}: No register function found in {module_path}"
                )
                return
            namespace = getattr(module, "NAMESPACE", module_name)
            _config = self.config.get(namespace)
            if _config is None:
                self.logger.warning(
                    f"Ignoring registering {module_name}: The expected config namespace '{namespace}' was not found."
                )
                return
            self.logger.debug(f"Registering {module_path}...")
            notification_client = register_func(_config, self.logger)
            if not issubclass(type(notification_client), BaseNotificationClient):
                self.logger.debug(
                    f"Ignoring registering {module_name}: Unsupported return type '{type(notification_client).__name__}'"
                )
                return
            self.notification_client.append(notification_client)
            self.logger.info(f"Registered notification client '{module_name}' successfully")
        except ModuleNotFoundError as e:
            if e.name == module_path:
                self.logger.error(f"Failed to import '{module_name}': '{module_path}' not found")
            else:
                self.logger.error(
                    f"Failed to registered '{module_name}' (most likely lacking of dependencies)"
                )
        except Exception as e:
            self.logger.exception(f"Failed to import {module_path}", exc_info=e)

    def load_notification_clients(self, path: str):
        """Load all notification clients in the specified directory"""
        path_split = re.compile(r"[\\/]")
        for _path in os.scandir(path):
            if _path.name.startswith("__"):
                continue
            if _path.is_file() and _path.name.endswith(".py"):
                module_path = re.sub(path_split, ".", _path.path)[:-3]
                is_module = False
            elif _path.is_dir():
                module_path = re.sub(path_split, ".", _path.path)
                is_module = True
            else:
                self.logger.debug(f"Ignoring importing unknown file type: {_path.name}")
                continue
            self.load_notification_client(module_path, is_module=is_module)
