import asyncio

import discord

from ..logging import Logger


class Bot(discord.AutoShardedBot):
    """
    The modified discord bot client.
    """

    def __init__(self, logger: Logger, config: dict, token: str) -> None:
        self.logger = logger
        self.config = config

        logger.disable("discord")  # avoid pycord shard info spamming the console

        self._client_ready = False
        intents = discord.Intents.default()
        super().__init__(owner_ids=self.config["discord"]["owners"], intents=intents)
        asyncio.create_task(self.start(token))

    async def on_ready(self) -> None:
        """
        The event that is triggered when the bot is ready.
        """
        if self._client_ready:
            return

        self.logger.info(
            f"""Discord Bot started.
-------------------------
Logged in as: {self.user.name}#{self.user.discriminator} ({self.user.id})
Shards Count: {self.shard_count}
 API Latency: {self.latency * 1000:.2f} ms
Guilds Count: {len(self.guilds)}
-------------------------"""
        )
        self._client_ready = True

    async def wait_until_ready(self) -> None:
        return await super().wait_until_ready()

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        return await super().start(token, reconnect=reconnect)

    async def close(self) -> None:
        await super().close()
        self.logger.info("Discord Bot closed.")
