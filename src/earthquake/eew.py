import io
from datetime import datetime

import matplotlib.pyplot as plt

from ..utils import MISSING
from .location import GEODATA, TOWN_RANGE, EarthquakeLocation, RegionLocation
from .model import Intensity, RegionExpectedIntensity, calculate_expected_intensity_and_travel_time

PROVIDER_DISPLAY = {
    "cwa": "中央氣象署",
}


class EarthquakeData:
    """
    Represents the data of an earthquake.
    """

    __slots__ = (
        "_location",
        "_magnitude",
        "_depth",
        "_time",
        "_max_intensity",
        "_expected_intensity",
        "_intensity_map",
    )

    def __init__(
        self,
        location: EarthquakeLocation,
        magnitude: float,
        depth: int,
        time: datetime,
        max_intensity: Intensity = MISSING,
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
        :param max_intensity: The maximum intensity of the earthquake.
        :type max_intensity: Intensity
        """
        self._location = location
        self._magnitude = magnitude
        self._depth = depth
        self._time = time
        self._max_intensity = max_intensity
        self._expected_intensity: dict[int, RegionExpectedIntensity] = None
        self._intensity_map: io.BytesIO = None

    @property
    def location(self) -> EarthquakeLocation:
        """
        The location object of the earthquake.
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

    @property
    def max_intensity(self) -> Intensity:
        """
        The maximum intensity of the earthquake.
        """
        return self._max_intensity

    @property
    def intensity_map(self) -> io.BytesIO:
        """
        The intensity map of the earthquake.
        """
        return self._intensity_map

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
            location=EarthquakeLocation(data["lon"], data["lat"], data.get("loc", MISSING)),
            magnitude=data["mag"],
            depth=data["depth"],
            time=datetime.fromtimestamp(data["time"] / 1000),
            max_intensity=Intensity(i) if (i := data.get("max")) else MISSING,
        )

    def calc_expected_intensity(
        self, regions: list[RegionLocation] = MISSING
    ) -> dict[int, RegionExpectedIntensity]:
        """
        Calculate the expected intensity of the earthquake.
        """
        self._expected_intensity = calculate_expected_intensity_and_travel_time(self, regions)
        return self._expected_intensity

    @property
    def expected_intensity(self) -> dict[int, RegionExpectedIntensity]:
        """
        The expected intensity of the earthquake.
        Format: {region_id: RegionExpectedIntensity, ...}
        """
        if self._expected_intensity is None:
            self.calc_expected_intensity()
        return self._expected_intensity

    def draw_map(self) -> str:
        """
        Draw the map of the earthquake.
        """
        if self._expected_intensity is None:
            self.calc_expected_intensity()

        fig, ax = plt.subplots(figsize=(16, 24))
        ax: plt.Axes
        fig.patch.set_alpha(0)
        ax.set_axis_off()
        # map boundary
        min_lon, max_lon = self.lon - 1.5, self.lon + 1.5
        min_lat, max_lat = self.lat - 2.2, self.lat + 2.2
        ax.set_xlim(min_lon, max_lon)
        ax.set_ylim(min_lat, max_lat)
        GEODATA.plot(ax=ax, color="lightgrey", edgecolor="black", linewidth=0.64)
        for code, region in self._expected_intensity.items():
            if region.intensity.value > 0:
                TOWN_RANGE[code].plot(ax=ax, color=region.intensity.color)
        # draw epicentre
        ax.scatter(self.lon, self.lat, marker="x", color="red", s=320, linewidths=8)
        self._intensity_map = io.BytesIO()
        fig.savefig(self._intensity_map, format="png", bbox_inches="tight")


class Provider:
    """
    Represents the data of an EEW provider.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        """
        Initialize an EEW provider data object.

        :param name: The name of the provider.
        :type name: str
        """
        self._name = name

    @property
    def name(self) -> str:
        """
        The name of the provider.
        """
        return self._name

    @property
    def display_name(self) -> str:
        """
        The display name of the provider.
        """
        return PROVIDER_DISPLAY.get(self._name, self._name)


class EEW:
    """
    Represents an earthquake early warning event.
    """

    __solts__ = ("_id", "_serial", "_final", "_earthquake", "_provider", "_time")

    def __init__(
        self,
        id: str,
        serial: int,
        final: bool,
        earthquake: EarthquakeData,
        provider: Provider,
        time: datetime,
    ) -> None:
        """
        Initialize an earthquake early warning event.

        :param id: The identifier of the EEW.
        :type id: str
        :param serial: The serial of the EEW.
        :type serial: int
        :param final: Whether the EEW is final report.
        :type final: bool
        :param earthquake: The data of the earthquake.
        :type earthquake: EarthquakeData
        :param provider: The provider of the EEW.
        :type provider: Provider
        :param time: The time when the EEW published.
        :type time: datetime
        """
        self._id = id
        self._serial = serial
        self._final = final
        self._earthquake = earthquake
        self._provider = provider
        self._time = time

    @property
    def id(self) -> str:
        """
        The identifier of the EEW.
        """
        return self._id

    @property
    def serial(self) -> int:
        """
        The serial of the EEW.
        """
        return self._serial

    @property
    def final(self) -> bool:
        """
        Whether the EEW is final report.
        """
        return self._final

    @property
    def earthquake(self) -> EarthquakeData:
        """
        The earthquake data of the EEW.
        """
        return self._earthquake

    @property
    def provider(self) -> Provider:
        """
        The provider of the EEW.
        """
        return self._provider

    @property
    def time(self) -> datetime:
        """
        The datetime object of the EEW.
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
            serial=data["serial"],
            final=bool(data["final"]),
            earthquake=EarthquakeData.from_dict(data=data["eq"]),
            provider=Provider(data["author"]),
            time=datetime.fromtimestamp(data["time"] / 1000),
        )
