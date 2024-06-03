import importlib
import logging
import os

from dotenv import load_dotenv

from .client.http import HTTPEEWClient
from .config import Config
from .logging import InterceptHandler, Logging

load_dotenv()


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

    client = HTTPEEWClient(config, logger)

    for root, dirs, files in os.walk("src/notification"):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                module_path = f"{root}.{module_name}".replace("/", ".")
                logger.debug(f"Importing {module_path}")
                try:
                    module = importlib.import_module(module_path)
                    register = getattr(module, "register", None)
                    if register is None:
                        logger.debug(f"No register function for {module_path}, ignoring")
                        continue
                    namespace = getattr(module, "NAMESPACE", module_name)
                    _config = config.get(namespace)
                    if _config is None:
                        logger.warning(f"No config '{namespace}' for {module_path}, ignoring")
                        continue
                    logger.debug(f"Registering {module_path}")
                    client.add_notification(register(_config, logger))
                    logger.info(f"Registered {module_path} successfully")
                except Exception as e:
                    logger.exception(f"Failed to import {module_path}", exc_info=e)

    client.run()
