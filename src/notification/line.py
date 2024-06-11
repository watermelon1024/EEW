import os

from linebot import LineBotApi
from linebot.models import TextSendMessage

from ..config import Config
from ..earthquake.eew import EEW
from ..logging import Logger
from .base import NotificationClient


class LineNotification(NotificationClient):
    """
    Represents a linebot EEW notification client.
    """

    alerts: dict[str, str] = {}
    notification_channels: list[str] = []

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

        for channel_id in self.config["channels"]:
            # TODO: check channel status
            self.notification_channels.append(channel_id)

        self.api = LineBotApi(access_token)

    async def run(self) -> None:
        """
        The entrypoint for the notification client.
        """
        self.logger.info("LINE Bot is ready")

    async def send_eew(self, eew: EEW) -> None:
        """
        If an new EEW is detected, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The EEW.
        :type eew: EEW
        """
        if len(self.notification_channels) == 0:
            self.logger.error("No LINE notification channels available")
            return
        eq = eew.earthquake
        summary = f"地震速報: {eq.location.display_name or eq.location}發生規模 M{eq.mag} 地震"
        image = f"https://static-maps.yandex.ru/1.x/?ll={eq.lon},{eq.lat}&z=10&l=map&size=450,450&pt={eq.lon},{eq.lat},round"
        provider = f"{eew.provider.display_name} ({eew.provider.name})"
        serial = f"編號: {eew.id} (第{eew.serial}報)"
        time = f"時間: {eq.time.strftime('%H:%M:%S')}"
        location = f"震央: {eq.location.display_name or eq.location}"
        magnitude = f"規模: M{eq.mag}"
        depth = f"深度: {eq.depth}公里"
        text = {
          "messages": [
            {
              "type": "flex",
              "altText": summary,
              "contents": {
                "type": "bubble",
                "header": {
                  "type": "box",
                  "layout": "vertical",
                  "contents": [
                    {
                      "type": "box",
                      "layout": "horizontal",
                      "contents": [
                        {
                          "type": "text",
                          "text": "地震速報",
                          "weight": "bold",
                          "size": "md",
                          "align": "start",
                          "gravity": "center"
                        },
                        {
                          "type": "text",
                          "text": provider,
                          "size": "sm",
                          "color": "#0000FFFF",
                          "align": "end",
                          "gravity": "center"
                        }
                      ]
                    },
                    {
                      "type": "text",
                      "text": serial
                    }
                  ]
                },
                "hero": {
                  "type": "image",
                  "url": image,
                  "align": "center",
                  "gravity": "center",
                  "size": "xxl",
                  "aspectRatio": "1:1"
                },
                "body": {
                  "type": "box",
                  "layout": "vertical",
                  "spacing": "md",
                  "contents": [
                    {
                      "type": "text",
                      "text": "慎防強烈搖晃，就近避難\n[趴下、掩護、穩住]",
                      "weight": "bold",
                      "size": "lg",
                      "align": "center",
                      "gravity": "top",
                      "wrap": true
                    },
                    {
                      "type": "separator"
                    },
                    {
                      "type": "box",
                      "layout": "vertical",
                      "contents": [
                        {
                          "type": "text",
                          "text": time,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        },
                        {
                          "type": "text",
                          "text": location,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        },
                        {
                          "type": "text",
                          "text": magnitude,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        },
                        {
                          "type": "text",
                          "text": depth,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        }
                      ]
                    }
                  ]
                },
                "footer": {
                  "type": "box",
                  "layout": "horizontal",
                  "spacing": "md",
                  "contents": [
                    {
                      "type": "button",
                      "action": {
                        "type": "uri",
                        "label": "地震報告",
                        "uri": "https://www.cwa.gov.tw/V8/C/E/index.html"
                      }
                    }
                  ]
                }
              }
            }
          ]
        }
        m = TextSendMessage(text=text)
        for channel_id in self.notification_channels:
            try:
                self.api.push_message(channel_id, messages=m)
            except Exception as e:
                self.logger.error(f"Failed to send EEW alert to {channel_id}: {e}")
            else:
                self.logger.info(f"Sent EEW alert to {channel_id}")

    async def update_eew(self, eew: EEW):
        """
        If an EEW is updated, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The updated EEW.
        :type eew: EEW
        """
        if len(self.notification_channels) == 0:
            self.logger.error("No LINE notification channels available")
            return
        eq = eew.earthquake
        summary = f"地震速報: {eq.location.display_name or eq.location}發生規模 M{eq.mag} 地震"
        provider = f"{eew.provider.display_name} ({eew.provider.name})"
        image = f"https://static-maps.yandex.ru/1.x/?ll={eq.lon},{eq.lat}&z=10&l=map&size=450,450&pt={eq.lon},{eq.lat},round"
        serial = f"編號: {eew.id} (第{eew.serial}報)"
        time = f"時間: {eq.time.strftime('%H:%M:%S')}"
        location = f"震央: {eq.location.display_name or eq.location}"
        magnitude = f"規模: M{eq.mag}"
        depth = f"深度: {eq.depth}公里"
        text = {
          "messages": [
            {
              "type": "flex",
              "altText": summary,
              "contents": {
                "type": "bubble",
                "header": {
                  "type": "box",
                  "layout": "vertical",
                  "contents": [
                    {
                      "type": "box",
                      "layout": "horizontal",
                      "contents": [
                        {
                          "type": "text",
                          "text": "地震速報",
                          "weight": "bold",
                          "size": "md",
                          "align": "start",
                          "gravity": "center"
                        },
                        {
                          "type": "text",
                          "text": provider,
                          "size": "sm",
                          "color": "#0000FFFF",
                          "align": "end",
                          "gravity": "center"
                        }
                      ]
                    },
                    {
                      "type": "text",
                      "text": serial
                    }
                  ]
                },
                "hero": {
                  "type": "image",
                  "url": image,
                  "align": "center",
                  "gravity": "center",
                  "size": "xxl",
                  "aspectRatio": "1:1"
                },
                "body": {
                  "type": "box",
                  "layout": "vertical",
                  "spacing": "md",
                  "contents": [
                    {
                      "type": "text",
                      "text": "慎防強烈搖晃，就近避難\n[趴下、掩護、穩住]",
                      "weight": "bold",
                      "size": "lg",
                      "align": "center",
                      "gravity": "top",
                      "wrap": true
                    },
                    {
                      "type": "separator"
                    },
                    {
                      "type": "box",
                      "layout": "vertical",
                      "contents": [
                        {
                          "type": "text",
                          "text": time,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        },
                        {
                          "type": "text",
                          "text": location,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        },
                        {
                          "type": "text",
                          "text": magnitude,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        },
                        {
                          "type": "text",
                          "text": depth,
                          "margin": "md",
                          "wrap": true
                        },
                        {
                          "type": "separator",
                          "margin": "md"
                        }
                      ]
                    }
                  ]
                },
                "footer": {
                  "type": "box",
                  "layout": "horizontal",
                  "spacing": "md",
                  "contents": [
                    {
                      "type": "button",
                      "action": {
                        "type": "uri",
                        "label": "地震報告",
                        "uri": "https://www.cwa.gov.tw/V8/C/E/index.html"
                      }
                    }
                  ]
                }
              }
            }
          ]
        }
        m = TextSendMessage(text=text)
        for channel_id in self.notification_channels:
            try:
                self.api.push_message(channel_id, messages=m)
            except Exception as e:
                self.logger.error(f"Failed to send EEW alert update to {channel_id}: {e}")
            else:
                self.logger.info(f"Sent EEW alert update to {channel_id}")

    async def lift_eew(self, eew: EEW):
        """
        If an EEW alert was lifted, this method will be called.

        Note: This method should not do any blocking calls.

        :param eew: The lifted EEW.
        :type eew: EEW
        """
        pass


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

    return LineNotification(logger, config, access_token, channel_secret)
