import asyncio
import json
import random
from collections import defaultdict
from enum import Enum
from typing import Any, Optional

import aiohttp
import aiohttp.client_exceptions
import aiohttp.http_exceptions
from aiohttp import ClientWebSocketResponse, WSMsgType

from ..earthquake.eew import EEW
from ..utils import MISSING
from .abc import EEWClient

DOMAIN = "exptech.dev"


class AuthorizationFailed(Exception):
    """Represents an authorization failure."""


class WebSocketReconnect(Exception):
    """Represents a websocket reconnect signal"""

    def __init__(self, reason: Any = None, *args: object) -> None:
        super().__init__(*args)
        self.reason = reason
        "The reason to reconnect the websocket"


class WebSocketEvent(Enum):
    Eew = "eew"
    Info = "info"
    Ntp = "ntp"
    Report = "report"
    Rts = "rts"
    Rtw = "rtw"
    Verify = "verify"
    Close = "close"
    Error = "error"


class SupportedService(Enum):
    RealtimeStation = "trem.rts"
    "即時地動資料"
    RealtimeWave = "trem.rtw"
    "即時地動波形圖資料"
    Eew = "websocket.eew"
    "地震速報資料"
    TremEew = "trem.eew"
    "TREM 地震速報資料"
    Report = "websocket.report"
    "中央氣象署地震報告資料"
    Tsunami = "websocket.tsunami"
    "中央氣象署海嘯資訊資料"
    CwaIntensity = "cwa.intensity"
    "中央氣象署震度速報資料"
    TremIntensity = "trem.intensity"
    "TREM 震度速報資料"


class WebSocketConnectionConfig:
    def __init__(
        self,
        key: str,
        service: list[SupportedService],
        config: Optional[dict[SupportedService, list[int]]] = None,
    ):
        """
        :param key: Authentication key
        :type key: str
        :param service: The services to subscribe
        :type service: list[SupportedService]
        :param config: Configuration for each service, defaults to None
        :type config: Optional[dict[SupportedService, list[int]]]
        """
        self.type = "start"
        self.key = key
        self.service = service
        self.config = config

    def to_dict(self):
        return {
            "type": self.type,
            "key": self.key,
            "service": [service.value for service in self.service],
            "config": self.config,
        }


# WebSocketAuthenticationInfo = Union[dict[str, Union[int, list[SupportedService]]], dict[str, Union[int, str]]]


class WebsocketClient(EEWClient):
    _alerts: dict[str, EEW] = {}
    __event_loop: Optional[asyncio.AbstractEventLoop] = MISSING
    __task: Optional[asyncio.Task] = MISSING
    __session: Optional[aiohttp.ClientSession] = MISSING
    ws: Optional[ClientWebSocketResponse] = MISSING
    subscribed_services: list[SupportedService | str] = []
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

    def get_websocket_route(self) -> str:
        return f"wss://lb-{random.randint(1, 4)}.{DOMAIN}/websocket"

    async def __wait_for_verify(self):
        """
        Return websocket message data if verify successfully

        :raise AuthorizationFailed: If the API key is invalid.
        :raise WebSocketReconnect: If the API key is already in used.
        """
        async for msg in self.ws:
            self.logger.debug(f"Received message: {msg.data}")
            if msg.type is WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == WebSocketEvent.Info.value:
                    data = data["data"]
                    message = data.get("message")
                    if message == "Invaild key!":
                        raise AuthorizationFailed
                    if message == "This key already in used!":
                        raise WebSocketReconnect("API key is already in used")
                    if message == "Subscripted service list":
                        return data

    async def verify(self):
        """
        Verify the API KEY and subscrible the services.

        :raise AuthorizationFailed: If the API key is invalid.
        :raise WebSocketReconnect: If the API key is already in used.
        :raise TimeoutError: If the verification times out.
        """
        config = self.websocket_config.to_dict()
        self.logger.debug(f"Sending config: {config}")
        await self.ws.send_json(config)
        try:
            data = await asyncio.wait_for(self.__wait_for_verify(), timeout=60)
            self.subscribed_services = data["list"]
            return data
        except TimeoutError as e:
            raise WebSocketReconnect("Verification timeout") from e

    async def connect(self):
        """Connect to the WebSocket"""
        if not self.__session:
            self.__session = aiohttp.ClientSession()

        in_reconnect = False
        while not self.__closed:
            try:
                if not self.ws or self.ws.closed:
                    self.ws = await self.__session.ws_connect(self.get_websocket_route())
                # send identify
                await self.verify()
                if not in_reconnect:
                    self.logger.info(
                        "EEW WebSocket is ready\n"
                        "--------------------------------------------------\n"
                        f"Subscribed services: {', '.join(self.subscribed_services)}\n"
                        "--------------------------------------------------"
                    )
                else:
                    self.logger.info(
                        "EEW WebSocket successfully reconnect\n"
                        "--------------------------------------------------\n"
                        f"Subscribed services: {', '.join(self.subscribed_services)}\n"
                        "--------------------------------------------------"
                    )
                self.__ready = True
                in_reconnect = False
                self._reconnect_delay = 0
                await self._loop()
            except AuthorizationFailed:
                await self.close()
                raise
            except WebSocketReconnect as e:
                await self.ws.close()
                in_reconnect = True
                self._reconnect_delay += 10
                self.logger.info(f"{e.reason}, reconnecting in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)
            except Exception as e:
                self.logger.exception("An error occurred, reconnecting...", exc_info=e)

    async def _loop(self):
        async for msg in self.ws:
            self.logger.debug(f"WebSocket received message: {msg}")
            if msg.type is WSMsgType.TEXT:
                await self._handle_message(msg.data)
            elif msg.type is aiohttp.WSMsgType.CLOSED:
                if self._reconnect:
                    raise WebSocketReconnect("WebSocket closed by server")
                return
            elif msg.type is WSMsgType.ERROR:
                await self._emit(WebSocketEvent.Error, self.ws.exception())

    async def _handle_message(self, raw: str):
        data = json.loads(raw)
        if data:
            await self._dispatch_event(data)

    async def _dispatch_event(self, data: dict[str, Any]):
        event_type = data.get("type")
        if event_type == WebSocketEvent.Verify.value:
            await self.verify()
        elif event_type == WebSocketEvent.Info.value:
            data = data.get("data", {})
            code = data.get("code")
            if code == 503:
                await asyncio.sleep(5)
                await self.verify()
            else:
                await self._emit(WebSocketEvent.Info, data)
        elif event_type == "data":
            data = data.get("data", {})
            data_type = data.get("type")
            if data_type:
                await self._emit(WebSocketEvent(data_type), data)
        elif event_type == WebSocketEvent.Ntp.value:
            await self._emit(WebSocketEvent.Ntp, data)

    async def _emit(self, event: WebSocketEvent, *args):
        for handler in self.event_handlers[event]:
            self.__event_loop.create_task(handler(*args))

    def on(self, event: WebSocketEvent, listener):
        self.event_handlers[event].append(listener)
        return self

    async def on_eew(self, data: dict):
        if data["author"] != "cwa":
            # only receive caw's eew
            return
        _check_finished_alerts = set(self._alerts.keys())
        id = data["id"]
        _check_finished_alerts.discard(id)
        eew = self._alerts.get(id)
        if eew is None:
            await self.new_alert(data)
        elif eew.serial != data["serial"]:
            await self.update_alert(data)

        # remove finished alerts
        for id in _check_finished_alerts:
            eew = self._alerts.pop(id, None)
            if eew is not None:
                await self.lift_alert(eew)

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
        self.on(WebSocketEvent.Eew, self.on_eew)
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
