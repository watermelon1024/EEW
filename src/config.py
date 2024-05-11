from typing import Any, Union

import tomli


class Config:
    """
    The a configuration class.
    """

    _path: str = "config.toml"
    with open(_path, "rb") as f:
        _config: dict = tomli.load(f)

    @classmethod
    def _load_config(cls) -> dict:
        """
        Load the configuration file.
        This is an internal method and should not be called directly.

        :raises TOMLDecodeError: Raised when the config is invalid.
        :raises FileNotFoundError: Raised when the file is not found.

        :return: The configuration file.
        :rtype: dict
        """
        with open(cls._path, "rb") as f:
            return tomli.load(f)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Union[str, Any]:
        """
        Get a key from the configuration file.

        :param key: The key to get.
        :type key: str
        :param default: The default value if the key is not found.
        :type default: Any, optional

        :return: The value of the key.
        :rtype: str, Any
        """
        return cls._config.get(key, default)

    @classmethod
    def reload(cls) -> None:
        """
        Reload the configuration file.
        """
        cls._config = cls._load_config()

    def __getitem__(self, key: str) -> Any:
        """
        Get a key from the configuration file.

        :param key: The key to get.
        :type key: str

        :return: The value of the key.
        :rtype: Any
        """
        return self._config[key]
