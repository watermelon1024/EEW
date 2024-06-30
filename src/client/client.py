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
from .http import HTTPClient
from .websocket import ExpTechWebSocket, WebSocketConnectionConfig


class Client:
    debug_mode: bool
    _http: "HTTPClient"
    _websocket: "ExpTechWebSocket"
    websocket_config: "WebSocketConnectionConfig"
    logger: Logger

