import asyncio
import random
import time
from typing import TYPE_CHECKING

import aiohttp

from ..logging import Logger
from .websocket import ExpTechWebSocket

if TYPE_CHECKING:
    from .client import Client


class HTTPClient:
    """A HTTP client for interacting with ExpTech API."""

    def __init__(
        self,
        logger: Logger,
        debug: bool,
        *,
        domain: str = "exptech.dev",
        api_version: int = 1,
        session: aiohttp.ClientSession = None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        self._logger = logger
        self._debug_mode = debug

        self.DOMAIN = domain
        self.__API_VERSION = api_version
        self.API_NODES = [
            *(f"https://api-{i}.{self.DOMAIN}/api/v{api_version}" for i in range(1, 3)),  # api-1 ~ api-2
            *(f"https://lb-{i}.{self.DOMAIN}/api/v{api_version}" for i in range(1, 5)),  # lb-1 ~ lb-4
        ]
        self.__base_url = self.API_NODES[0]
        self.node_latencies = [(node, float("inf")) for node in self.API_NODES]
        self.__current_node_index = 0
        self.WS_NODES = [f"wss://lb-{i}.{self.DOMAIN}/websocket" for i in range(1, 5)]  # lb-1 ~ lb-4
        self._current_ws_node = self.WS_NODES[0]
        self.ws_node_latencies = [(node, float("inf")) for node in self.WS_NODES]
        self._current_ws_node_index = 0

        self._loop = loop or asyncio.get_event_loop()
        self._session = session or aiohttp.ClientSession(
            loop=self._loop,
            headers={"User-Agent": "EEW/1.0.0 (https://github.com/watermelon1024/EEW)"},
        )
        self._session._ws_response_class = ExpTechWebSocket

    # http api node
    async def _test_latency(self, url: str) -> float:
        try:
            start = time.time()
            async with self._session.get(url) as response:
                if response.ok:
                    latency = time.time() - start
                    return latency
                else:
                    return float("inf")
        except Exception:
            return float("inf")

    async def test_api_latencies(self):
        """Test all API nodes latencies"""
        latencies = [(node, await self._test_latency(f"{node}/eq/eew")) for node in self.API_NODES]
        latencies.sort(key=lambda x: x[1])
        self.node_latencies = latencies
        return latencies

    def switch_api_node(self, type_or_url: str = "next"):
        """
        Switch the API node.

        :param type_or_url: The type or url of the API node. Type supports `next`, `fastest` and `random`.
        :type type_or_url: str
        """

        if type_or_url == "next":
            idx = (self.__current_node_index + 1) % len(self.node_latencies)
        elif type_or_url == "fastest":
            idx = 0
        elif type_or_url == "random":
            idx = random.randint(0, len(self.node_latencies) - 1)
        else:
            idx = None

        if idx is None:
            url = type_or_url
        else:
            url = self.node_latencies[idx][0]
            self.__current_node_index = idx
        self.__base_url = url
        self._logger.info(f"Switched to API node: {url}")

    async def request(self, method: str, path: str, *, json: bool = True, retry: int = 0, **kwargs):
        """
        Make a request to the API.

        :param method: The HTTP method to use.
        :type method: str
        :param path: The path to request.
        :type path: str
        :param json: Whether to return the response as JSON.
        :type json: bool
        :param retry: The number of retries if the request fails.
        :type retry: int
        :param kwargs: Additional keyword arguments to pass to the request.
        :type kwargs: dict
        :return: The response from the API.
        :rtype: str | dict | Any
        """
        url = self.__base_url + path
        try:
            async with self._session.request(method, url, **kwargs) as r:
                resp = await r.json() if json else await r.text()
                self._logger.debug(f"{method} {url} receive {r.status}: {resp}")
                return resp
        except Exception as e:
            if isinstance(e, aiohttp.ContentTypeError):
                self._logger.debug(
                    f"Fail to decode JSON when {method} {url} (receive {r.status}): {await r.text()}"
                )
            else:
                self._logger.debug(f"Fail to {method} {url}: {e}")
            self.switch_api_node()
            if retry > 0:
                await asyncio.sleep(1)
                return await self.request(method, path, json=json, retry=retry - 1, **kwargs)
            raise

    async def get(self, path: str, retry: int = 0, **kwargs):
        """
        Make a GET request to the API.

        :param path: The path to request.
        :type path: str
        :param retry: The number of retries if the request fails.
        :type retry: int
        :param kwargs: Additional keyword arguments to pass to the request.
        :type kwargs: dict
        :return: The response from the API.
        :rtype: str | dict | Any
        """
        return await self.request("GET", path, retry=retry, **kwargs)

    async def post(self, path: str, data: dict, retry: int = 0, **kwargs):
        """
        Make a POST request to the API.

        :param path: The path to request.
        :type path: str
        :param data: The data to send in the request body.
        :type data: dict
        :param retry: The number of retries if the request fails.
        :type retry: int
        :param kwargs: Additional keyword arguments to pass to the request.
        :type kwargs: dict
        :return: The response from the API.
        :rtype: str | dict | Any
        """
        return await self.request("POST", path, data=data, retry=retry, **kwargs)

    # websocket node
    async def _test_ws_latency(self, url: str) -> float:
        try:
            async with self._session.ws_connect(url) as ws:
                await ws.receive(timeout=5)  # discard first ntp

                start_time = time.time()
                await ws.send_json({"type": "start"})
                await ws.receive()
                latency = time.time() - start_time
                return latency
        except Exception:
            return float("inf")

    async def test_ws_latencies(self):
        """Test all websocket nodes latencies"""
        latencies = [(node, await self._test_ws_latency(node)) for node in self.WS_NODES]
        latencies.sort(key=lambda x: x[1])
        self.ws_node_latencies = latencies
        return latencies

    def switch_ws_node(self, type_or_url: str = "next"):
        """
        Switch the websocket node.

        :param type_or_url: The type or url of the websocket node. Type supports `next`, `fastest` and `random`.
        :type type_or_url: str
        """

        if type_or_url == "next":
            idx = (self._current_ws_node_index + 1) % len(self.ws_node_latencies)
        elif type_or_url == "fastest":
            idx = 0
        elif type_or_url == "random":
            idx = random.randint(0, len(self.ws_node_latencies) - 1)
        else:
            idx = None

        if idx is None:
            url = type_or_url
        else:
            url = self.ws_node_latencies[idx][0]
            self._current_ws_node_index = idx
        self._current_ws_node = url
        self._logger.info(f"Switched to websocket node: {url}")

    async def ws_connect(self, client: "Client"):
        """
        Connect to the websocket.
        """
        if not self._current_ws_node:
            self._current_ws_node = self.WS_NODES[0]
        return await ExpTechWebSocket.connect(client)
