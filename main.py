import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)


def main():
    from src import Client, Config, InterceptHandler, Logging, WebSocketConnectionConfig, WebSocketService

    config = Config()
    logger = Logging(
        retention=config["log"]["retention"],
        debug_mode=config["debug-mode"],
        format=config["log"]["format"],
    ).get_logger()
    logging.basicConfig(
        handlers=[InterceptHandler(logger)],
        level=0 if config["debug-mode"] else logging.INFO,
        force=True,
    )

    key = os.getenv("API_KEY")
    if key:
        logger.info("API_KEY found, using WebSocket Client")
        ws_config = WebSocketConnectionConfig(
            key=key, service=[WebSocketService.EEW, WebSocketService.TREM_EEW]
        )

    else:
        logger.info("API_KEY not found, using HTTP Client")
        ws_config = None

    client = Client(config=config, logger=logger, websocket_config=ws_config, debug=config["debug-mode"])
    client.load_notification_clients("notification")
    client.run()

    logger.remove()


if __name__ == "__main__":
    main()
