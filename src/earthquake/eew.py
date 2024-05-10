from datetime import datetime

from .location import EarthquakeLocation


class EarthquakeData:
    """
    Represents the data of an earthquake.
    """

    __slots__ = ("_location", "_magnitude", "_depth", "_time")

    def __init__(
        self,
        location: EarthquakeLocation,
        magnitude: float,
        depth: int,
        time: datetime,
    ) -> None:
        """
        Initialize an earthquake data object.

        :param location: The location of the earthquake.
        :type location: EarthquakeLocation
        :param magnitude: The magnitude of the earthquake.
        :type magnitude: float
        :param depth: The depth of the earthquake in km.
        :type depth: int
        :param time: The time when earthquake happened.
        :type time: datetime
        """
        self._location = location
        self._magnitude = magnitude
        self._depth = depth
        self._time = time

    @property
    def location(self) -> EarthquakeLocation:
        """
        The location of the earthquake.
        """
        return self._location

    @property
    def lon(self) -> float:
        """
        The longitude of the earthquake.
        """
        return self._location.lon

    @property
    def lat(self) -> float:
        """
        The latitude of the earthquake.
        """
        return self._location.lat

    @property
    def mag(self) -> float:
        """
        The magnitude of the earthquake.
        """
        return self._magnitude

    @property
    def depth(self) -> int:
        """
        The depth of the earthquake in km.
        """
        return self._depth

    @property
    def time(self) -> datetime:
        """
        The time when earthquake happened.
        """
        return self._time

    @classmethod
    def from_dict(cls, data: dict) -> "EarthquakeData":
        """
        Create an earthquake data object from the dictionary.

        :param data: The data of the earthquake from the api.
        :type data: dict
        :return: The earthquake data object.
        :rtype: EarthquakeData
        """
        return cls(
            location=EarthquakeLocation(data["lon"], data["lat"], data.get("loc")),
            magnitude=data["mag"],
            depth=data["depth"],
            time=datetime.fromtimestamp(data["time"] / 1000),
        )


class EEW:
    """
    Represents an earthquake early warning event.
    """

    __solts__ = ("_id", "_earthquake", "_provider", "_time")

    def __init__(
        self,
        id: str,
        earthquake: EarthquakeData,
        provider: str,
        time: datetime,
    ) -> None:
        """
        Initialize an eew event.

        :param id: The identifier of the EEW.
        :type id: str
        :param earthquake: The data of the earthquake.
        :type earthquake: EarthquakeData
        :param provider: The provider of the EEW.
        :type provider: str
        :param time: The time when the EEW published.
        :type time: datetime
        """
        self._id = id
        self._earthquake = earthquake
        self._provider = provider
        self._time = time

    @property
    def id(self) -> str:
        """
        The identifier of the earthquake.
        """
        return self._id

    @property
    def earthquake(self) -> EarthquakeData:
        """
        The data of the earthquake.
        """
        return self._earthquake

    @property
    def time(self) -> datetime:
        """
        The datetime object of the earthquake.
        """
        return self._time

    @classmethod
    def from_dict(cls, data: dict) -> "EEW":
        """
        Create an EEW object from the data dictionary.

        :param data: The data of the earthquake from the api.
        :type data: dict
        :return: The EEW object.
        :rtype: EEW
        """
        return cls(
            id=data["id"],
            earthquake=EarthquakeData.from_dict(data=data["eq"]),
            provider=data["provider"],
            time=datetime.fromtimestamp(data["time"] / 1000),
        )
