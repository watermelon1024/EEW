from abc import ABC

from ..earthquake.eew import EEW


class BaseNotificationClient(ABC):
    """
    An ABC for notification client.
    """

    async def send_eew(self, eew: EEW):
        pass

    async def update_eew(self, eew: EEW):
        pass

    async def lift_eew(self, eew: EEW):
        pass

    async def start(self):
        """Start the notification client in async"""
        pass
