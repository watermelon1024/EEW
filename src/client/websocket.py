import asyncio
import json
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Union

import aiohttp

from ..logging import Logger

if TYPE_CHECKING:
    from .client import Client


class AuthorizationFailed(Exception):
    """Represents an authorization failure."""


class WebSocketReconnect(Exception):
    """Represents a websocket reconnect signal."""

    def __init__(
        self, reason: Any = None, reopen: bool = False, source_exc: Exception = None, *args: object
    ) -> None:
        """Represents a websocket reconnect signal.

        :param reason: The reason to reconnect the websocket, defaults to None
        :type reason: Any
        :param reopen: Whether to reopen the websocket, defaults to False
        :type reopen: bool
        """
        super().__init__(*args)
        self.reason = reason
        self.reopen = reopen
        self.source_exc = source_exc


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

    __client: "Client"
    _logger: Logger
    config: WebSocketConnectionConfig
    subscribed_services: list[Union[WebSocketService, str]]
    __wait_until_ready: asyncio.Event

    async def debug_receive(self, timeout: float | None = None) -> aiohttp.WSMessage:
        msg = await super().receive(timeout)
        self._logger.debug(f"Websocket received: {msg}")
        return msg

    async def debug_send_str(self, data: str, compress: int | None = None) -> None:
        self._logger.debug(f"Websocket sending: {data}")
        return await super().send_str(data, compress)

    @classmethod
    async def connect(cls, client: "Client", **kwargs):
        """
        Connect to the websocket.
        """
        self: cls = await client._http._session.ws_connect(client._http._current_ws_node, **kwargs)
        self.__client = client
        self._logger = client.logger
        self.config = client.websocket_config
        self.subscribed_services = []
        if client.debug_mode:
            self.receive = self.debug_receive
            self.send_str = self.debug_send_str

        self.__wait_until_ready = asyncio.Event()
        await self.verify()
        # while not self.__wait_until_ready.is_set():
        #     await self.pool_event()

        return self

    async def send_verify(self):
        """
        Send the verify data to the websocket.
        """
        data = self.config.to_dict()
        data["type"] = "start"
        await self.send_json(data)

    async def verify(self):
        """
        Verify the websocket connection.

        :return the subscribed services.
        :rtype: list[SupportedService]
        """
        await self.send_verify()
        data = await asyncio.wait_for(self.wait_for_verify(), timeout=60)
        self.subscribed_services = data["list"]
        self.__wait_until_ready.set()
        return self.subscribed_services

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
            if data.get("type") == WebSocketEvent.VERIFY.value:
                await self.send_verify()
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
                raise WebSocketReconnect("API key is already in used", reopen=True)
            elif code == 401:
                # no api key or invalid api key
                raise AuthorizationFailed(message)
            elif code == 403:
                # vip membership expired
                raise AuthorizationFailed(message)
            elif code == 429:
                raise WebSocketReconnect("Rate limit exceeded", reopen=True)

    async def wait_until_ready(self):
        """Wait until websocket client is ready"""
        await self.__wait_until_ready.wait()

    async def receive_and_check(self):
        """
        Receives message and check if it is handleable.

        :return: A handleable message.
        :rtype: aiohttp.WSMessage

        :raise WebSocketException: If the message is not handleable.
        :raise WebSocketClosure: If the websocket is closed.
        """

        msg = await self.receive(timeout=90)
        if msg.type is aiohttp.WSMsgType.TEXT:
            return msg
        elif msg.type is aiohttp.WSMsgType.BINARY:
            return msg
        elif msg.type is aiohttp.WSMsgType.ERROR:
            raise WebSocketException(msg)
        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
            raise WebSocketClosure
        else:
            raise WebSocketException(msg, "Websocket received unhandleable message")

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
            data_ = data.get("data", {})
            code = data_.get("code")
            if code == 503:
                await asyncio.sleep(5)
                await self.verify()
            else:
                await self._emit(WebSocketEvent.INFO.value, data_)
        elif event_type == "data":
            time = data.get("time")
            data_ = data.get("data", {})
            data_["time"] = time
            data_type = data_.get("type")
            if data_type:
                await self._emit(data_type, data_)
        elif event_type == WebSocketEvent.NTP.value:
            await self._emit(WebSocketEvent.NTP.value, data)

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
            raise WebSocketReconnect("Websocket closed", reopen=True, source_exc=e) from e
        except asyncio.TimeoutError as e:
            raise WebSocketReconnect("Websocket message received timeout", reopen=False) from e
        except WebSocketException as e:
            self._logger.error(f"Websocket received an error: {e.description or e.message.data}", exc_info=e)
