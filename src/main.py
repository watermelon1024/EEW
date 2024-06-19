import importlib
import logging
import os

from dotenv import load_dotenv

from .config import Config
from .logging import InterceptHandler, Logging
from .notification.base import NotificationClient

load_dotenv(override=True)


def main():
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
        from .client.websocket import SupportedService, WebsocketClient, WebSocketConnectionConfig

        logger.info("API_KEY found, using WebSocket Client")
        ws_config = WebSocketConnectionConfig(
            key=key, service=[SupportedService.EEW, SupportedService.TREM_EEW]
        )
        client = WebsocketClient(config=config, logger=logger, websocket_config=ws_config)
    else:
        from .client.http import HTTPEEWClient

        logger.info("API_KEY not found, using HTTP Client")
        client = HTTPEEWClient(config=config, logger=logger)

    for path in os.scandir("src/notification"):
        if path.name == "base.py" or path.name == "template" or path.name.startswith("__"):
            continue
        if path.is_file() and path.name.endswith(".py"):
            module_name = path.name[:-3]
            module_path = f"src.notification.{module_name}"
        elif path.is_dir():
            module_name = path.name
            module_path = f"src.notification.{module_name}.register"
        else:
            logger.debug(f"Ignoring importing unknown file type: {path.name}")
            continue
        try:
            logger.debug(f"Importing {module_path}...")
            module = importlib.import_module(module_path)
            register_func = getattr(module, "register", None)
            if register_func is None:
                logger.debug(
                    f"Ignoring registering {module_name}: No register function found in {module_path}"
                )
                continue
            namespace = getattr(module, "NAMESPACE", module_name)
            _config = config.get(namespace)
            if _config is None:
                logger.warning(
                    f"Ignoring registering {module_name}: The expected config namespace '{namespace}' was not found."
                )
                continue
            logger.debug(f"Registering {module_path}...")
            notification_client = register_func(_config, logger)
            if not issubclass(type(notification_client), NotificationClient):
                logger.debug(
                    f"Ignoring registering {module_name}: Unsupport return type '{type(notification_client).__name__}'"
                )
                continue
            client.add_notification(notification_client)
            logger.success(f"Registered notification client '{module_name}' successfully")
        except ModuleNotFoundError as e:
            if e.name == module_path:
                logger.error(f"Failed to import '{module_name}': '{module_path}' not found")
            else:
                logger.error(f"Failed to registered '{module_name}' (most likely lacking of dependencies)")
        except Exception as e:
            logger.exception(f"Failed to import {module_path}", exc_info=e)

    client.run()
    logger.remove()
