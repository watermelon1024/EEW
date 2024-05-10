import json


class Location:
    """
    A base class represents a location with longitude and latitude.
    """

    __slots__ = ("_longitude", "_latitude")

    def __init__(self, longitude: float, latitude: float):
        """
        Initialize a Location object.

        :param longitude: The longitude of the location.
        :type longitude: float
        :param latitude: The latitude of the location.
        :type latitude: float
        """
        self._longitude = longitude
        self._latitude = latitude

    @property
    def lon(self):
        """The longitude of the location."""
        return self._longitude

    @property
    def lat(self):
        """The latitude of the loaction."""
        return self._latitude

    def __str__(self):
        return f"({self._longitude}, {self._latitude})"

    def __repr__(self):
        return f"Location({self._longitude}, {self._latitude})"

    def __iter__(self):
        yield from (self._longitude, self._latitude)

    def __eq__(self, other):
        return (
            issubclass(other, Location)
            and self._longitude == other._longitude
            and self._latitude == other._latitude
        )

    def __hash__(self):
        return hash((self._longitude, self._latitude))

    def to_dict(self) -> dict[str, float]:
        """
        Return the location as a dictionary.

        :return: The location as a dictionary.
        :rtype: dict[str, float]
        """
        return {"longitude": self._longitude, "latitude": self._latitude}


class EarthquakeLocation(Location):
    """
    Represents a earthquake location.
    """

    __slots__ = ("_longitude", "_latitude", "_display_name")

    def __init__(self, longitude: float, latitude: float, display: str = None):
        """
        Initialize a earthquake location object.

        :param longitude: The longitude of the location.
        :type longitude: float
        :param latitude: The latitude of the location.
        :type latitude: float
        :param display: The display name of the location.
        :type display: str
        """
        super().__init__(longitude, latitude)
        self._display_name = display

    @property
    def display_name(self):
        """The display name of the location."""
        return self._display_name


class RegionLocation(Location):
    """
    Represents a region with longitude, latitude, region code and name.
    """

    __slots__ = ("_longitude", "_latitude", "_code", "_name")

    def __init__(
        self,
        longitude: float,
        latitude: float,
        code: int = None,
        name: str = None,
        city: str = None,
        area: str = None,
        site_effect: float = None,
    ):
        """
        Initialize the region object.

        :param longitude: The longitude of the region.
        :type longitude: float
        :param latitude: The latitude of the region.
        :type latitude: float
        :param code: The identifier of the region.
        :type code: int
        :param name: The name of the region.
        :type name: str
        :param city: The city of the region.
        :type city: str
        :param area: The area of the region.
        :type area: str
        :param site_effect: The site effect of the region.
        :type site_effect: float
        """
        super().__init__(longitude, latitude)
        self._code = code
        self._name = name
        self._city = city
        self._area = area
        self._site_effect = site_effect

    @property
    def lon(self):
        """The longitude of the location."""
        return self._longitude

    @property
    def lat(self):
        """The latitude of the loaction."""
        return self._latitude

    @property
    def code(self):
        """The identifier of the location."""
        return self._code

    @property
    def name(self):
        """The name of the location."""
        return self._name

    @property
    def city(self):
        """The city of the location."""
        return self._city

    @property
    def area(self):
        """The area of the location."""
        return self._area

    @property
    def side_effect(self):
        """The site effect of the location."""
        return self._site_effect

    def __str__(self):
        return f"{self._name}({self._longitude}, {self._latitude})"

    def __repr__(self):
        return f"RegionLocation({self._name} at ({self._longitude}, {self._latitude})"


def _parse_region_dict(data: dict[str, dict[str, int | float | str]]) -> dict[int, RegionLocation]:
    all_regions = {}
    for city, regoins in data.items():
        for name, d in regoins.items():
            all_regions[d["code"]] = RegionLocation(
                d["lon"], d["lat"], d["code"], name, city, d["area"], d["site_effect"]
            )
    return all_regions


with open("../asset/region.json", "r", encoding="utf-8") as f:
    REGIONS: dict[int, RegionLocation] = _parse_region_dict(json.load(f))