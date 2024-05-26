"""
Earthquake expected data calculator.

Reference: https://github.com/ExpTechTW/TREM-tauri/blob/main/src/scripts/helper/utils.ts
"""

import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, OrderedDict

import numpy as np
from obspy.taup import tau
from scipy.interpolate import interp1d

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

    __slots__ = ("_km", "_deg", "_p_arrival_time", "_s_arrival_time", "_p_travel_time", "_s_travel_time")

    def __init__(
        self,
        in_km: float,
        in_degrees: float,
        p_arrival_time: datetime,
        s_arrival_time: datetime,
        p_travel_time: float,
        s_travel_time: float,
    ) -> None:
        """
        Initialize the distance instance.

        :param in_km: The distance in kilometers.
        :type in_km: float
        :param in_degrees: The distance in degrees.
        :type in_degrees: float
        :param p_arrival_time: P wave arrival time.
        :type p_arrival_time: datetime
        :param s_arrival_time: S wave arrival time.
        :type s_arrival_time: datetime
        :param p_travel_time: P travel time.
        :type p_travel_time: float
        :param s_travel_time: S travel time.
        :type s_travel_time: float
        """
        self._km = in_km
        self._deg = in_degrees
        self._p_arrival_time = p_arrival_time
        self._s_arrival_time = s_arrival_time
        self._p_travel_time = p_travel_time
        self._s_travel_time = s_travel_time

    @property
    def km(self) -> float:
        """
        The distance from the hypocenter in km.
        """
        return self._km

    @property
    def degrees(self) -> float:
        """
        The distance from the epicenter in degrees.
        """
        return self._deg

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


class RegionExpectedIntensities(dict):
    """
    Represents a dict like object of expected intensity for each region returned by :method:`calculate_expected_intensity_and_travel_time`.
    """

    __slots__ = ("distances", "p_travel_time", "s_travel_time")

    def __init__(self, intensities: dict[int, RegionExpectedIntensity]):
        """
        Initialize the region expected intensities instance.

        :param intensities: The intensities.
        :type intensities: dict[int, RegionExpectedIntensity]
        """
        super(RegionExpectedIntensities, self).__init__()
        self.update(intensities)

        distances, p_travel_time, s_travel_time = map(
            np.array,
            zip(
                *(
                    (i.distance.degrees, i.distance.p_travel_time, i.distance.s_travel_time)
                    for i in intensities.values()
                    if i is not None
                )
            ),
        )
        self.distances: np.ndarray[float] = distances
        "The distances in degrees."
        self.p_travel_time: np.ndarray[float] = p_travel_time
        "The P wave travel time in seconds."
        self.s_travel_time: np.ndarray[float] = s_travel_time
        "The S wave travel time in seconds."

    def __getitem__(self, key: int) -> RegionExpectedIntensity:
        return super().__getitem__(key)

    def get(self, key: int, default=None) -> RegionExpectedIntensity:
        return super().get(key, default)


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
    pga = 1.657 * math.exp(1.533 * magnitude) * hypocenter_distance**-1.607 * (site_effect or 1.751)
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
) -> RegionExpectedIntensities:
    """
    Calculate the expected intensity and travel time of the earthquake in different regions.

    :param earthquake: EarthquakeData object containing earthquake information.
    :type earthquake: EarthquakeData
    :param regions: List of RegionLocation to calculate. If missing, it will calculate all existing regions.
    :type regions: list[RegionLocation]
    :return: RegionExpectedIntensities object containing expected intensity and travel time for each region.
    :rtype: RegionExpectedIntensities
    """

    _expected_intensity = {}
    failed_regions: list[tuple[RegionLocation, float, float]] = []

    for region in regions or REGIONS.values():
        distance_in_radians = _calculate_distance(earthquake, region)
        distance_in_degrees = math.degrees(distance_in_radians)
        arrivals = MODEL.get_travel_times(
            source_depth_in_km=earthquake.depth,
            distance_in_degree=distance_in_degrees,
            phase_list=["p", "s"],
        )
        if len(arrivals) != 2:
            failed_regions.append((region, distance_in_radians, distance_in_degrees))
            _expected_intensity[region.code] = None
            continue

        p_arrival, s_arrival = arrivals
        p_arrival: tau.Arrival
        s_arrival: tau.Arrival

        distance_in_km = p_arrival.purist_dist * EARTH_RADIUS
        intensity = _calculate_intensity(distance_in_km, earthquake.mag, earthquake.depth, region.side_effect)

        _expected_intensity[region.code] = RegionExpectedIntensity(
            region,
            Intensity(intensity),
            Distance(
                distance_in_km,
                distance_in_degrees,
                earthquake.time + timedelta(seconds=p_arrival.time),
                earthquake.time + timedelta(seconds=s_arrival.time),
                p_arrival.time,
                s_arrival.time,
            ),
        )

    intensities = RegionExpectedIntensities(_expected_intensity)

    p_travel_time_interp_func = interp1d(
        intensities.distances,
        intensities.p_travel_time,
        fill_value="extrapolate",
    )
    s_travel_time_interp_func = interp1d(
        intensities.distances,
        intensities.s_travel_time,
        fill_value="extrapolate",
    )

    for region, rad, deg in failed_regions:
        p_travel_time = float(p_travel_time_interp_func(deg))
        s_travel_time = float(s_travel_time_interp_func(deg))
        distance_in_km = math.sqrt((rad * EARTH_RADIUS) ** 2 + earthquake.depth**2)
        intensity = _calculate_intensity(distance_in_km, earthquake.mag, earthquake.depth, region.side_effect)

        intensities[region.code] = RegionExpectedIntensity(
            region,
            Intensity(intensity),
            Distance(
                distance_in_km,
                deg,
                earthquake.time + timedelta(seconds=p_travel_time),
                earthquake.time + timedelta(seconds=s_travel_time),
                p_travel_time,
                s_travel_time,
            ),
        )

    return intensities
