import logging

from ..config import Config
from ..earthquake.location import RegionLocation
from ..logging import InterceptHandler, Logging
from ..utils import MISSING


class EEWClient:
    """
    Represents a base EEW API Client.
    """

    __slots__ = ("_alert_regions", "_calc_site_effect", "config", "debug_mode", "logger")

    def __init__(
        self,
        alert_regions: list[RegionLocation] = MISSING,
        calculate_site_effect: bool = False,
    ) -> None:
        self._alert_regions = alert_regions
        self._calc_site_effect = calculate_site_effect

        self.config = Config()
        self.debug_mode: bool = self.config["client"]["debug-mode"]
        self.logger = Logging(
            retention=self.config["log"]["retention"],
            debug_mode=self.debug_mode,
            format=self.config["log"]["format"],
        ).get_logger()
        logging.basicConfig(
            handlers=[InterceptHandler(self.logger)],
            level=0 if self.debug_mode else logging.INFO,
            force=True,
        )

