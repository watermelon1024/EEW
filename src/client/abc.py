import asyncio
from abc import ABC, abstractmethod

from ..config import Config
from ..earthquake.location import RegionLocation
from ..logging import Logger
from ..notification.abc import NotificationClient
from ..utils import MISSING


class EEWClient(ABC):
    """
    An ABC represents a base EEW API Client.
    """

    def __init__(
        self,
        config: Config,
        logger: Logger,
        alert_regions: list[RegionLocation] = MISSING,
        calculate_site_effect: bool = False,
        notification_client: list[NotificationClient] = MISSING,
        api_version: int = 1,
    ) -> None:
        self.config = config
        self.debug_mode: bool = config["debug-mode"]
        self.logger = logger

        self._alert_regions = alert_regions
        self._calc_site_effect = calculate_site_effect
        self._notification_client = notification_client or []

        self._API_VERSION = api_version
        self.BASE_URL = f"https://api-2.exptech.com.tw/api/v{api_version}"

    def add_notification(self, client: NotificationClient):
        """
        Add a notification client.
        """
        self._notification_client.append(client)

    def run_notification_client(self):
        """
        Run all the notification clients in event loop.
        """
        self.__event_loop = asyncio.get_event_loop()
        for client in self._notification_client:
            self.__event_loop.create_task(client.run())

    @abstractmethod
    def run(self):
        pass
