import asyncio
import json
import random
from collections import defaultdict
from enum import Enum
from typing import Any, Optional, Union

import aiohttp

from ..earthquake.eew import EEW
from ..logging import Logger
from ..utils import MISSING
from .abc import EEWClient

DOMAIN = "exptech.dev"


class AuthorizationFailed(Exception):
    """Represents an authorization failure."""


class WebSocketReconnect(Exception):
    """Represents a websocket reconnect signal."""

    def __init__(self, reason: Any = None, reopen: bool = False, *args: object) -> None:
        """Represents a websocket reconnect signal.

        :param reason: The reason to reconnect the websocket, defaults to None
        :type reason: Any
        :param reopen: Whether to reopen the websocket, defaults to False
        :type reopen: bool
        """
        super().__init__(*args)
        self.reason = reason
        self.reopen = reopen


class WebSocketClosure(Exception):
    """Represents a websocket closed signal."""


class WebSocketException(Exception):
    """Represents a websocket exception."""

    def __init__(self, message: aiohttp.WSMessage, description: str = None, *args: object) -> None:
        """
        Represents a websocket exception.

        :param message: The websocket message that caused the exception.
        :type message: aiohttp.WSMessage
        :param description: The description of the exception.
        :type description: str
        """
        super().__init__(*args)
        self.description = description
        self.message = message


class WebSocketEvent(Enum):
    """Represent the websocket event"""

    EEW = "eew"
    INFO = "info"
    NTP = "ntp"
    REPORT = "report"
    RTS = "rts"
    RTW = "rtw"
    VERIFY = "verify"
    CLOSE = "close"
    ERROR = "error"


class WebSocketService(Enum):
    """Represent the supported websokcet service"""

    REALTIME_STATION = "trem.rts"
    "即時地動資料"
    REALTIME_WAVE = "trem.rtw"
    "即時地動波形圖資料"
    EEW = "websocket.eew"
    "地震速報資料"
    TREM_EEW = "trem.eew"
    "TREM 地震速報資料"
    REPORT = "websocket.report"
    "中央氣象署地震報告資料"
    TSUNAMI = "websocket.tsunami"
    "中央氣象署海嘯資訊資料"
    CWA_INTENSITY = "cwa.intensity"
    "中央氣象署震度速報資料"
    TREM_INTENSITY = "trem.intensity"
    "TREM 震度速報資料"


class WebSocketConnectionConfig:
    """
    Represents the configuration for the websocket connection.
    """

    def __init__(
        self,
        key: str,
        service: list[WebSocketService],
        config: Optional[dict[WebSocketService, list[int]]] = None,
    ):
        """
        :param key: Authentication key
        :type key: str
        :param service: The services to subscribe
        :type service: list[SupportedService]
        :param config: Configuration for each service, defaults to None
        :type config: Optional[dict[SupportedService, list[int]]]
        """
        self.key = key
        self.service = service
        self.config = config

    def to_dict(self):
        return {
            "key": self.key,
            "service": [service.value for service in self.service],
            "config": self.config,
        }


# WebSocketAuthenticationInfo = Union[dict[str, Union[int, list[SupportedService]]], dict[str, Union[int, str]]]


class ExpTechWebSocket(aiohttp.ClientWebSocketResponse):
    """
    A websocket connection to the ExpTech API.
    """

    __client: "WebsocketClient"
    logger: Logger
    config: WebSocketConnectionConfig
    subscribed_services: list[Union[WebSocketService, str]]

    async def debug_receive(self, timeout: float | None = None) -> aiohttp.WSMessage:
        msg = await super().receive(timeout)
        self.logger.debug(f"Websocket received: {msg}")
        return msg

    @classmethod
    def get_route(cls) -> str:
        """Get a random websocket node."""
        return f"wss://lb-{random.randint(1, 4)}.{DOMAIN}/websocket"

    @classmethod
    async def connect(cls, client: "WebsocketClient", session: aiohttp.ClientSession, **kwargs):
        """
        Connect to the websocket.
        """
        session._ws_response_class = cls
        self: cls = await session.ws_connect(cls.get_route(), **kwargs)
        self.__client = client
        self.logger = client.logger
        self.config = client.websocket_config
        self.subscribed_services = []
        if client.debug_mode:
            self.receive = self.debug_receive

        await self.verify()

        return self

    async def start(self):
        """
        Send the start signal to the websocket.
        """
        data = self.config.to_dict()
        data["type"] = "start"
        await self.send_json(data)

    async def verify(self):
        """
        Verify the websocket connection.
        """
        await self.start()
        data = await asyncio.wait_for(self.wait_for_verify(), timeout=60)
        self.subscribed_services = data["list"]

    async def wait_for_verify(self):
        """
        Return websocket message data if verify successfully

        :return: The data of the verify result
        :rtype: dict

        :raise AuthorizationFailed: If the API key is invalid.
        :raise WebSocketReconnect: If the API key is already in used.
        :raise WebSocketClosure: If the websocket is closed.
        """
        while True:
            msg = await self.receive_and_check()
            data = json.loads(msg.data)
            if data.get("type") != WebSocketEvent.INFO.value:
                continue

            data = data["data"]
            message = data.get("message")
            code = data.get("code")
            if code == 200:
                # subscribe successfully
                return data
            elif code == 400:
                # api key in used
                raise WebSocketReconnect("API key is already in used", reopen=True) from None
            elif code == 401:
                # no api key or invalid api key
                raise AuthorizationFailed(message) from None
            elif code == 403:
                # vip membership expired
                raise AuthorizationFailed(message) from None
            elif code == 429:
                raise WebSocketReconnect("Rate limit exceeded", reopen=True) from None

    async def receive_and_check(self):
        """
        Receives message and check if it is handleable.

        :return: A handleable message.
        :rtype: aiohttp.WSMessage

        :raise WebSocketException: If the message is not handleable.
        :raise WebSocketClosure: If the websocket is closed.
        """

        msg = await self.receive()
        if msg.type is aiohttp.WSMsgType.TEXT:
            return msg
        elif msg.type is aiohttp.WSMsgType.BINARY:
            return msg
        elif msg.type is aiohttp.WSMsgType.ERROR:
            raise WebSocketException(msg) from None
        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
            raise WebSocketClosure from None
        else:
            raise WebSocketException(msg, "Websocket received unhandleable message") from None

    async def _handle(self, msg: aiohttp.WSMessage):
        if msg.type is aiohttp.WSMsgType.TEXT:
            await self._handle_json(json.loads(msg.data))
        elif msg.type is aiohttp.WSMsgType.BINARY:
            await self._handle_binary(msg.data)

    async def _handle_binary(self, data: bytes):
        pass

    async def _handle_json(self, data: dict):
        event_type = data.get("type")
        if event_type == WebSocketEvent.VERIFY.value:
            await self.verify()
        elif event_type == WebSocketEvent.INFO.value:
            data = data.get("data", {})
            code = data.get("code")
            if code == 503:
                await asyncio.sleep(5)
                await self.verify()
            else:
                await self._emit(WebSocketEvent.INFO, data)
        elif event_type == "data":
            time = data.get("time")
            data_ = data.get("data", {})
            data_["time"] = time
            data_type = data_.get("type")
            if data_type:
                await self._emit(WebSocketEvent(data_type), data_)
        elif event_type == WebSocketEvent.NTP.value:
            await self._emit(WebSocketEvent.NTP, data)

    @property
    def _emit(self):
        return self.__client._emit

    async def pool_event(self):
        try:
            msg = await self.receive_and_check()
            await self._handle(msg)
        except WebSocketReconnect:
            raise
        except WebSocketClosure as e:
            raise WebSocketReconnect("Websocket closed", reopen=True) from e
        except asyncio.TimeoutError as e:
            raise WebSocketReconnect("Websocket message received timeout", reopen=False) from e
        except WebSocketException as e:
            self.logger.error(f"Websocket received an error: {e.description or e.message.data}", exc_info=e)


class WebsocketClient(EEWClient):
    _alerts: dict[str, EEW] = {}
    __event_loop: Optional[asyncio.AbstractEventLoop] = MISSING
    __task: Optional[asyncio.Task] = MISSING
    __session: Optional[aiohttp.ClientSession] = MISSING
    ws: Optional[ExpTechWebSocket] = MISSING
    subscribed_services: list[Union[WebSocketService, str]] = []
    event_handlers = defaultdict(list)
    __ready = False
    _reconnect = True
    _reconnect_delay = 0
    __closed = False

    def __init__(self, *args, websocket_config: WebSocketConnectionConfig, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket_config = websocket_config

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

    async def connect(self):
        """Connect to the WebSocket"""
        if not self.__session:
            self.__session = aiohttp.ClientSession(ws_response_class=ExpTechWebSocket)

        in_reconnect = False
        while not self.__closed:
            try:
                if not self.ws or self.ws.closed:
                    self.subscribed_services.clear()
                    self.logger.debug("Connecting to WebSocket...")
                    self.ws = await ExpTechWebSocket.connect(self, self.__session)
                    if not self.__ready:
                        self.logger.info(
                            "EEW WebSocket is ready\n"
                            "--------------------------------------------------\n"
                            f"Subscribed services: {', '.join(self.ws.subscribed_services)}\n"
                            "--------------------------------------------------"
                        )
                    self.__ready = True
                if in_reconnect:
                    self.logger.info(
                        "EEW WebSocket successfully reconnect\n"
                        "--------------------------------------------------\n"
                        f"Subscribed services: {', '.join(self.ws.subscribed_services)}\n"
                        "--------------------------------------------------"
                    )
                in_reconnect = False
                self._reconnect_delay = 0
                while True:
                    await self.ws.pool_event()
            except AuthorizationFailed:
                await self.close()
                raise
            except WebSocketReconnect as e:
                if e.reopen and self.ws and not self.ws.closed:
                    await self.ws.close()
                in_reconnect = True
                self._reconnect_delay += 10
                self.logger.exception(
                    f"Attempting a reconnect in {self._reconnect_delay}s: {e.reason}", exc_info=e
                )
                await asyncio.sleep(self._reconnect_delay)
            except Exception as e:
                self._reconnect_delay += 10
                self.logger.exception(
                    f"An unhandleable error occurred, reconnecting in {self._reconnect_delay}s", exc_info=e
                )
                await asyncio.sleep(self._reconnect_delay)

    async def _emit(self, event: WebSocketEvent, *args):
        for handler in self.event_handlers[event]:
            self.__event_loop.create_task(handler(*args))

    def on(self, event: WebSocketEvent, listener):
        self.event_handlers[event].append(listener)
        return self

    async def on_eew(self, data: dict):
        self.logger.info(data)
        if data["author"] != "cwa":
            # only receive caw's eew
            return
        eew = self._alerts.get(data["id"])
        if eew is None:
            await self.new_alert(data)
        elif data["serial"] > eew.serial:
            await self.update_alert(data)

    async def close(self):
        """Close the websocket"""
        self._reconnect = False
        self.__closed = True
        if self.ws:
            await self.ws.close()

    def closed(self):
        """Whether the websocket is closed"""
        return self.__closed

    async def start(self):
        """
        Start the client.
        Note: This coro won't finish forever until user interrupt it.
        """
        self.logger.info("Starting EEW WebSocket Client...")
        self.on(WebSocketEvent.EEW, self.on_eew)
        self.run_notification_client()
        await self.connect()

    def run(self):
        """
        Start the client.
        Note: This is a blocking call. If you want to control your own event loop, use `start` instead.
        """
        self.__event_loop = asyncio.get_event_loop()
        self.__event_loop.create_task(self.start())
        try:
            self.__event_loop.run_forever()
        except KeyboardInterrupt:
            self.__event_loop.run_until_complete(self.close())
            self.__event_loop.stop()
        finally:
            self.logger.info("EEW WebSocket has been stopped.")
