"""
Earthquake expected data calculator.

Reference: https://github.com/ExpTechTW/TREM-tauri/blob/main/src/scripts/helper/utils.ts
"""

import math
from typing import TYPE_CHECKING

from ..utils import MISSING
from .location import REGIONS, Location

if TYPE_CHECKING:
    from .eew import EarthquakeData

EARTH_RADIUS = 6371.008


def _calculate_surface_distance(p1: Location, p2: Location) -> float:
    """
    Calculate the distance between two points on the Earth's surface.

    :param p1: The location object.
    :type p1: Location
    :param p2: The location object.
    :type p2: Location
    :return: The distance between the two points in kilometers.
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
    d = EARTH_RADIUS * c
    return d


def _calculate_distance(earthquake: "EarthquakeData", location: Location) -> tuple[float, float]:
    """
    Calculate the surface and actual distances from the hypocenter to the specific location.

    :param earthquake: The earthquake data.
    :type earthquake: EarthquakeData
    :param location: The specific location.
    :type location: Location
    :return: The surface and actual distances in kilometers.
    :rtype: tuple[float, float]
    """
    surface_distance = _calculate_surface_distance(earthquake, location)
    distance = math.sqrt(surface_distance**2 + earthquake.depth**2)
    return surface_distance, distance


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


def calculate_rigon_intensity(
    surface_distance: float,
    hypocenter_distance: float,
    magnitude: float,
    depth: int,
    site_effect: float = 1.751,
) -> float:
    """
    Calculate the intensity of the earthquake in a given location.

    :param surface_distance: Surface distance from the epicenter to the specific point in kilometers.
    :type surface_distance: float
    :param hypocenter_distance: Actual distance from the hypocenter to the specific point in kilometers.
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


def calculate_expected_intensity(
    earthquake: "EarthquakeData", regions: list = MISSING
) -> dict[int, int]:
    """
    Calculate the expected intensity of the earthquake in different regions.

    :param earthquake: EarthquakeData object containing earthquake information.
    :type earthquake: EarthquakeData
    :param regions: List of RegionLocation to calculate. If missing, it will calculate all existing regions.
    :type regions: list
    :return: Dictionary containing the expected intensity for each region.
    :rtype: dict
    """
    expected_intensity = {}

    # TODO: Add support for custom external regions
    for region in regions or REGIONS.values():
        surface_distance, distance = _calculate_distance(earthquake, region)
        intensity = calculate_rigon_intensity(
            surface_distance, distance, earthquake.mag, earthquake.depth
        )
        expected_intensity[region.code] = round_intensity(intensity)

    return expected_intensity


def calculate_travel_time(depth: int, distance: float) -> tuple[float, float]:
    """
    Calculate the P and S wave travel times based on the earthquake depth and distance.

    :param depth: Depth of the earthquake in kilometers.
    :type depth: int
    :param distance: Actual distance from the hypocenter to the specific point in kilometers.
    :type distance: float
    :return: P and S wave travel times.
    :rtype: tuple[float, float]
    """
    # speed model
    Za = depth
    if depth <= 40:
        G0, G = 5.10298, 0.06659
    else:
        G0, G = 7.804799, 0.004573
    Zc = -1 * (G0 / G)
    Xb = distance
    Xc = (Xb**2 - 2 * (G0 / G) * Za - Za**2) / (2 * Xb)

    Theta_a = math.atan((Za - Zc) / Xc)
    if Theta_a < 0:
        Theta_a += math.pi
    Theta_a = math.pi - Theta_a

    Theta_B = math.atan((-1 * Zc) / (Xb - Xc))
    p_time = (1 / G) * math.log(math.tan(Theta_a / 2) / math.tan(Theta_B / 2))

    G0_, G_ = G0 / 1.732, G / 1.732
    Zc_ = -1 * (G0_ / G_)
    Xc_ = (Xb**2 - 2 * (G0_ / G_) * Za - Za**2) / (2 * Xb)

    Theta_A_ = math.atan((Za - Zc_) / Xc_)
    if Theta_A_ < 0:
        Theta_A_ += math.pi
    Theta_A_ = math.pi - Theta_A_

    Theta_B_ = math.atan((-1 * Zc_) / (Xb - Xc_))
    s_time = (1 / G_) * math.log(math.tan(Theta_A_ / 2) / math.tan(Theta_B_ / 2))

    if distance / p_time > 7:
        p_time = distance / 7
    if distance / s_time > 4:
        s_time = distance / 4

    return p_time, s_time
