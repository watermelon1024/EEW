from abc import ABC, abstractmethod
from earthquake.eew import EEW


class NotificationClient(ABC):
    """
    An ABC for notification client.
    """

    @abstractmethod
    async def send_eew(self, eew: EEW):
        pass

    @abstractmethod
    async def update_eew(self, eew: EEW):
        pass
