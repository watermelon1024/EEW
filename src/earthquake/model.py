"""
Earthquake expected data calculator.

Reference: https://github.com/ExpTechTW/TREM-tauri/blob/main/src/scripts/helper/utils.ts
"""

import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, OrderedDict

from obspy.taup import tau

from ..utils import MISSING
from .location import REGIONS, Location, RegionLocation

if TYPE_CHECKING:
    from .eew import EarthquakeData

MODEL_CACHE = OrderedDict()
MODEL = tau.TauPyModel(cache=MODEL_CACHE)
EARTH_RADIUS = 6371.008
INTENSITY_DISPLAY: dict[int, str] = {
    0: "0級",
    1: "1級",
    2: "2級",
    3: "3級",
    4: "4級",
    5: "5弱",
    6: "5強",
    7: "6弱",
    8: "6強",
    9: "7級",
}
INTENSITY_COLOR: dict[int, str] = {
    0: None,
    1: "#244FA6",
    2: "#387AFF",
    3: "#359D56",
    4: "#E9CD40",
    5: "#E9AE5A",
    6: "#E96914",
    7: "#FF6161",
    8: "#E93769",
    9: "#491475",
}


class Intensity:
    """
    Represents an intensity.
    """

    __slots__ = ("_float_value", "_value", "_display", "_color")

    def __init__(self, value: float) -> None:
        """
        Initialize the intensity instance.

        :param value: The intensity.
        :type value: float
        """
        self._float_value = value
        self._value = round_intensity(value)
        self._display = INTENSITY_DISPLAY[self._value]
        self._color = INTENSITY_COLOR[self._value]

    @property
    def value(self) -> int:
        """
        The intensity.
        """
        return self._value

    @property
    def display(self) -> str:
        """
        Get the intensity display string.
        """
        return self._display

    @property
    def color(self) -> str:
        """
        Get the intensity color.
        """
        return self._color

    def __str__(self) -> str:
        return self._display

    def __repr__(self) -> str:
        return f"Intensity({self._float_value:.2f})"


class Distance:
    """
    Represents a distance and travel time.
    """

    __slots__ = ("_distance", "_p_arrival_time", "_s_arrival_time", "_p_travel_time", "_s_travel_time")

    def __init__(
        self,
        value: float,
        p_arrival_time: datetime,
        s_arrival_time: datetime,
        p_travel_time: float,
        s_travel_time: float,
    ) -> None:
        """
        Initialize the distance instance.

        :param value: The distance.
        :type value: float
        :param p_arrival_time: P wave arrival time.
        :type p_arrival_time: datetime
        :param s_arrival_time: S wave arrival time.
        :type s_arrival_time: datetime
        :param p_travel_time: P travel time.
        :type p_travel_time: float
        :param s_travel_time: S travel time.
        :type s_travel_time: float
        """
        self._distance = value
        self._p_arrival_time = p_arrival_time
        self._s_arrival_time = s_arrival_time
        self._p_travel_time = p_travel_time
        self._s_travel_time = s_travel_time

    @property
    def distance(self) -> float:
        """
        The distance from the hypocenter.
        """
        return self._distance

    @property
    def p_arrival_time(self) -> datetime:
        """
        P wave arrival time.
        """
        return self._p_arrival_time

    @property
    def s_arrival_time(self) -> datetime:
        """
        S wave arrival time.
        """
        return self._s_arrival_time

    @property
    def p_travel_time(self) -> float:
        """
        P travel time.
        """
        return self._p_travel_time

    @property
    def s_travel_time(self) -> float:
        """
        S travel time.
        """
        return self._s_travel_time

    def p_left_time(self, now: datetime = MISSING) -> timedelta:
        """
        P wave remaining time.
        """
        return self._p_arrival_time - (now or datetime.now())

    def s_left_time(self, now: datetime = MISSING) -> timedelta:
        """
        S wave remaining time.
        """
        return self._s_arrival_time - (now or datetime.now())


class RegionExpectedIntensity:
    """
    Represents a region expected intensity.
    """

    def __init__(self, region: RegionLocation, intensity: Intensity, distance: Distance) -> None:
        """
        Initialize the region expected intensity instance.

        :param region: The region.
        :type region: RegionLocation
        :param intensity: The intensity.
        :type intensity: Intensity
        :param distance: The distance.
        :type distance: Distance
        """
        self._region = region
        self._intensity = intensity
        self._distance = distance

    @property
    def region(self) -> RegionLocation:
        """
        The region.
        """
        return self._region

    @property
    def intensity(self) -> Intensity:
        """
        The intensity.
        """
        return self._intensity

    @property
    def distance(self) -> Distance:
        """
        The distance.
        """
        return self._distance

    def __repr__(self) -> str:
        return f"RegionExpectedIntensity({self._region}, {self._intensity}, {self._distance.s_arrival_time})"


def _calculate_distance(p1: Location, p2: Location) -> float:
    """
    Calculate the distance between two points on the Earth's surface.

    :param p1: The location object.
    :type p1: Location
    :param p2: The location object.
    :type p2: Location
    :return: The distance between the two points in radians.
    :rtype: float
    """
    # haversine formula
    lon1 = math.radians(p1.lon)
    lat1 = math.radians(p1.lat)
    lon2 = math.radians(p2.lon)
    lat2 = math.radians(p2.lat)
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c


def round_intensity(intensity: float) -> int:
    """
    Round the floating-point intensity value to the nearest integer.

    :param intensity: Floating-point intensity value.
    :type intensity: float
    :return: Rounded intensity value.
    :rtype: int
    """
    if intensity < 0:
        return 0
    elif intensity < 4.5:
        return round(intensity)
    elif intensity < 5:
        return 5
    elif intensity < 5.5:
        return 6
    elif intensity < 6:
        return 7
    elif intensity < 6.5:
        return 8
    else:
        return 9


def _calculate_intensity(
    hypocenter_distance: float,
    magnitude: float,
    depth: int,
    site_effect: float = 1.751,
) -> float:
    """
    Calculate the intensity of the earthquake of a given distance.

    :param hypocenter_distance: Actual distance from the hypocenter in kilometers.
    :type hypocenter_distance: float
    :param magnitude: Magnitude of the earthquake.
    :type magnitude: float
    :param depth: Depth of the earthquake in kilometers.
    :type depth: int
    :param site_effect: Site effect factor, default is 1.751.
    :type site_effect: float
    :return: Estimated intensity.
    :rtype: float
    """
    pga = 1.657 * math.exp(1.533 * magnitude) * hypocenter_distance**-1.607 * site_effect
    i = 2 * math.log10(pga) + 0.7

    if i > 3:
        long = 10 ** (0.5 * magnitude - 1.85) / 2
        x = max(hypocenter_distance - long, 3)
        gpv600 = 10 ** (
            0.58 * magnitude
            + 0.0038 * depth
            - 1.29
            - math.log10(x + 0.0028 * 10 ** (0.5 * magnitude))
            - 0.002 * x
        )
        arv = 1.0
        pgv400 = gpv600 * 1.31
        pgv = pgv400 * arv
        i = 2.68 + 1.72 * math.log10(pgv)

    return i


def calculate_expected_intensity_and_travel_time(
    earthquake: "EarthquakeData", regions: list[RegionLocation] = MISSING
) -> dict[int, RegionExpectedIntensity]:
    """
    Calculate the expected intensity and travel time of the earthquake in different regions.

    :param earthquake: EarthquakeData object containing earthquake information.
    :type earthquake: EarthquakeData
    :param regions: List of RegionLocation to calculate. If missing, it will calculate all existing regions.
    :type regions: list[RegionLocation]
    """

    expected_intensity = {}

    for region in regions or REGIONS.values():
        distance_in_radians = _calculate_distance(earthquake, region)
        distance_in_degrees = math.degrees(distance_in_radians)
        distance_in_km = EARTH_RADIUS * distance_in_radians
        intensity = _calculate_intensity(distance_in_km, earthquake.mag, earthquake.depth)
        arrivals = MODEL.get_travel_times(
            source_depth_in_km=earthquake.depth,
            distance_in_degree=distance_in_degrees,
            phase_list=["p", "s"],
        )
        if len(arrivals) == 2:
            p_arrival, s_arrival = arrivals
        else:
            arrivals = MODEL.get_travel_times(
                source_depth_in_km=earthquake.depth,
                distance_in_degree=distance_in_degrees,
                phase_list=["P", "S"],
            )
            p_arrival = None
            s_arrival = None
            for arrival in arrivals:
                arrival: tau.Arrival
                if arrival.name == "P" and p_arrival is None:
                    p_arrival = arrival
                elif arrival.name == "S" and s_arrival is None:
                    s_arrival = arrival

        expected_intensity[region.code] = RegionExpectedIntensity(
            region,
            Intensity(intensity),
            Distance(
                distance_in_km,
                earthquake.time + timedelta(seconds=p_arrival.time),
                earthquake.time + timedelta(seconds=s_arrival.time),
                p_arrival.time,
                s_arrival.time,
            ),
        )

    return expected_intensity
