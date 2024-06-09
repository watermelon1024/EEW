import os, uuid
from ..config import Config
from ..earthquake.eew import EEW
from ..logging import Logger
from .abc import NotificationClient

from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    BroadcastRequest,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

class LineNotification(NotificationClient):
    """
    Represents a [custom] EEW notification client.
    """

    def __init__(self, logger: Logger, config: Config, access_token: str, channel_secret: str) -> None:
        """
        Initialize a new linebot notification client.

        :param logger: The logger instance.
        :type logger: Logger
        :param config: The configuration.
        :type config: Config
        :param access_token: The LINE Messaging API access token.
        :type access_token: str
        :param channel_secret: The LINE Messaging API channel secret.
        :type channel_secret: str
        """
        self.logger = logger
        self.config = config
                
        self.app = Flask(__name__)

        self.configuration = Configuration(access_token=access_token)
        self.configuration = Configuration(channel_secret=channel_secret)
        self.configuration = Configuration(host = config['host'])
        
        self._client_ready = False

    async def run(self) -> None:
        """
        The entrypoint for the notification client.
        """
        self.logger.info("Starting linebot Notification Client...")
        pass # no need to run the event loop

    async def send_eew(self, eew: EEW):
        """
        If an new EEW is detected, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The EEW.
        :type eew: EEW
        """
        with ApiClient(self.configuration) as api_client:
            # Create an instance of the API class
            api_instance = MessagingApi(api_client)

            broadcast_request = BroadcastRequest() # BroadcastRequest | 
            # x_line_retry_key = str(uuid.uuid4()) # str | Retry key. 

            try:
                # api_response = api_instance.broadcast(broadcast_request, x_line_retry_key=x_line_retry_key)
                api_response = api_instance.broadcast(broadcast_request)
                print("The response of MessagingApi->broadcast:\n")
                print(api_response)
            except Exception as e:
                print("Exception when calling MessagingApi->broadcast: %s\n" % e)

    async def update_eew(self, eew: EEW):
        """
        If an EEW is updated, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The updated EEW.
        :type eew: EEW
        """
        ...

    async def lift_eew(self, eew: EEW):
        """
        If an EEW alert was lifted, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The lifted EEW.
        :type eew: EEW
        """
        ...


NAMESPACE = "line-bot"


def register(config: Config, logger: Logger) -> None:
    """
    Register the linebot notification client.

    Note: DO NOT run or start the client in this function, just register it.
    If you want to run it in the event loop, do it in :method:`NotificationClient.run`.

    :param config: The configuration of linebot notification client.
    :type config: Config
    :param logger: The logger instance.
    :type logger: Logger
    """
    access_token = os.environ.get("LINEBOT_ACCESS_TOKEN")
    channel_secret = os.environ.get("LINEBOT_CHANNEL_SECRET")
    if access_token is None or channel_secret is None:
        logger.error(f"{NAMESPACE} LINEBOT_ACCESS_TOKEN or LINEBOT_CHANNEL_SECRET is not set")
        return

    return LineNotification(logger, config)
