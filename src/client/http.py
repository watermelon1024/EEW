import asyncio
import random
import time

import aiohttp

from ..logging import Logger
from ..utils import MISSING
from .websocket import ExpTechWebSocket


class HTTPClient:
    """An HTTP client for interacting with ExpTech API."""

    DOMAIN = "exptech.dev"

    node_latencies: list[tuple[str, float]] = []
    _current_node_index: int = 0

    def __init__(
        self,
        logger: Logger,
        debug: bool,
        *,
        api_version: int = 1,
        session: aiohttp.ClientSession = MISSING,
        loop: asyncio.AbstractEventLoop = MISSING,
    ):
        self._logger = logger
        self._debug_mode = debug

        self.API_NODES = [
            f"https://api-{i}.{self.DOMAIN}/api/v{api_version}" for i in range(1, 3)
        ]  # api-1 ~ api-2
        self.WS_NODES = [f"wss://lb-{i}.{self.DOMAIN}/websocket" for i in range(1, 5)]  # lb-1 ~ lb-4

        self._loop = loop or asyncio.get_event_loop()
        self._session = session or aiohttp.ClientSession(loop=self._loop)
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

    async def test_api_latency(self):
        """Test all API nodes latency"""
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
            idx = (self._current_node_index + 1) % len(self.node_latencies)
        elif type_or_url == "fastest":
            idx = 0
        elif type_or_url == "random":
            idx = random.randint(0, len(self.node_latencies) - 1)
        else:
            idx = MISSING
            raise ValueError(f"Invalid type: {type_or_url}")

        url = type_or_url if idx is MISSING else self.node_latencies[idx][0]
        self._current_node_index = idx
        self._session._base_url = aiohttp.client.URL(url)
        self._logger.info(f"Switched to API node: {url}")

    async def get(self, path: str, retry: int = 0):
        try:
            async with self._session.get(path) as r:
                data: list[dict] = await r.json()
                if not data:
                    return None
        except Exception:
            if retry > 0:
                self.switch_api_node()
                await asyncio.sleep(1)
                return await self.get(retry - 1)
            raise

    async def post(self, path: str, data: dict, retry: int = 0):
        try:
            async with self._session.post(path, json=data) as r:
                data: dict = await r.json()
        except Exception:
            if retry > 0:
                self.switch_api_node()
                await asyncio.sleep(1)
                return await self.post(retry - 1)
            raise
