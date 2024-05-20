from typing import Optional, TypedDict

from discord import TextChannel


class NotifyAndChannel(TypedDict):
    channel: TextChannel
    mention: Optional[str]
