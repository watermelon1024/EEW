"""
ExpTech API Client
~~~~~~~~~~~~~~~~~~~

A simple wrapper to connect to ExpTech EEW API
"""

from .client.client import Client
from .client.http import HTTPClient
from .client.websocket import (
    AuthorizationFailed,
    ExpTechWebSocket,
    WebSocketConnectionConfig,
    WebSocketEvent,
    WebSocketReconnect,
    WebSocketService,
)
from .config import Config
from .earthquake.eew import EEW, EarthquakeData, Provider
from .earthquake.location import (
    COUNTRY_DATA,
    REGIONS,
    REGIONS_GROUP_BY_CITY,
    TAIWAN_CENTER,
    EarthquakeLocation,
    Location,
    RegionLocation,
)
from .earthquake.map import Map
from .earthquake.model import (
    Distance,
    Intensity,
    RegionExpectedIntensities,
    RegionExpectedIntensity,
    WaveModel,
    calculate_expected_intensity_and_travel_time,
    get_wave_model,
    round_intensity,
)
from .logging import InterceptHandler, Logger, Logging
from .notification.base import BaseNotificationClient
from .utils import MISSING
