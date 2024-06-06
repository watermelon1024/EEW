import asyncio
import json
import random
from collections import defaultdict
from enum import Enum
from typing import Any, Optional

import aiohttp
from aiohttp import ClientWebSocketResponse, WSMsgType

from ..earthquake.eew import EEW
from ..utils import MISSING
from .abc import EEWClient

DOMAIN = "exptech.dev"


class AuthorizationFailed(Exception):
    """
    Represents an authorization failure.
    """


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
    ws: Optional[ClientWebSocketResponse] = MISSING
    event_handlers = defaultdict(list)
    _connect_retry_delay = 0

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
        return f"wss://lb-{random.randint(1,4)}.{DOMAIN}/websocket"

    async def verify(self):
        """Send the verify data"""
        await self.ws.send_json(self.websocket_config.to_dict())

    async def _loop(self):
        while True:
            try:
                if self.ws and not self.ws.closed:
                    await self.ws.close()

                async with aiohttp.ClientSession() as session, session.ws_connect(
                    self.get_websocket_route()
                ) as ws:
                    self.ws = ws
                    await self.verify()

                    async for msg in ws:
                        self.logger.debug(f"WebSocket received message: {msg}")
                        if msg.type == WSMsgType.TEXT:
                            await self._handle_message(msg.data)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            break
                        elif msg.type == WSMsgType.ERROR:
                            await self._emit(WebSocketEvent.Error, ws.exception())
            except AuthorizationFailed as e:
                raise e
            except aiohttp.ClientConnectorError as e:
                self.logger.exception("Connection failed, retrying...", exc_info=e)
            except Exception as e:
                self.logger.exception("Unexpected error", exc_info=e)
            # retry in 5 seconds
            await asyncio.sleep(5)

    async def _handle_message(self, raw: str):
        try:
            data = json.loads(raw)
            if data:
                await self._dispatch_event(data)
        except Exception as error:
            await self._emit(WebSocketEvent.Error, error)

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

    async def on_info(self, data: dict):
        message = data.get("message")
        code = data.get("code")
        if "already in used" in message:
            self._connect_retry_delay += 60
            self.logger.error(
                f"Authentication key is already in used, retry in {self._connect_retry_delay} seconds..."
            )
            await asyncio.sleep(self._connect_retry_delay)
            await self.verify()
        elif code == 401:
            self.logger.error("Invaild authentication key.")
            raise AuthorizationFailed("Invaild authentication key.")

    async def on_eew(self, data: dict):
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

    async def update_config(self, websocket_config: WebSocketConnectionConfig):
        self.websocket_config = websocket_config
        await self.verify()

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def start(self):
        """
        Start the client.
        Note: This coro won't finish forever until user interrupt it.
        """
        self.logger.info("Starting EEW WebSocket Client...")
        self.on(WebSocketEvent.Eew, self.on_eew)
        self.on(WebSocketEvent.Info, self.on_info)
        self.run_notification_client()
        await self._loop()

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
            self.__event_loop.stop()
        finally:
            self.logger.info("EEW WebSocket has been stopped.")
