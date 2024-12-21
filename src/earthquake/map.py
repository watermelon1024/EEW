import io
import warnings
from collections import defaultdict
from typing import TYPE_CHECKING

import geopandas as gpd
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from .location import COUNTRY_DATA, TAIWAN_CENTER, TOWN_DATA, TOWN_RANGE

if TYPE_CHECKING:
    from earthquake.eew import EarthquakeData

plt.ioff()
plt.switch_backend("AGG")

P_WAVE_COLOR = "orange"
S_WAVE_COLOR = "red"
INTENSITY_COLOR: dict[int, str] = {
    0: None,
    1: "#387FFF",
    2: "#244FD0",
    3: "#35BF56",
    4: "#F8F755",
    5: "#FFC759",
    6: "#FF9935",
    7: "#DF443B",
    8: "#7B170F",
    9: "#7237C1",
}
legend_img = mpimg.imread("asset/map_legend.png")
legend_offset = OffsetImage(legend_img, zoom=0.5)


class Map:
    """
    Represents the map for earthquake.
    """

    __slots__ = ("_eq", "_image", "fig", "ax", "_drawn", "p_wave", "s_wave")

    def __init__(self, earthquake: "EarthquakeData"):
        """
        Initialize the map.

        :param lon: longitude of the epicenter
        :param lat: latitude of the epicenter
        """
        self._eq = earthquake
        self._image = None
        self._drawn: bool = False
        "Whether the map has been drawn"

        self.fig: plt.Figure = None
        "The figure object of the map"
        self.ax: plt.Axes = None
        "The axes of the figure"
        self.p_wave: plt.Circle = None
        "The p-wave of the earthquake"
        self.s_wave: plt.Circle = None
        "The s-wave of the earthquake"

    def init_figure(self):
        """
        Initialize the figure of the map.
        """
        self.fig, self.ax = plt.subplots(figsize=(4, 6))
        self.fig.patch.set_alpha(0)
        self.ax.set_axis_off()

    @property
    def image(self) -> io.BytesIO:
        """
        The map image of the earthquake.
        """
        return self._image

    def draw(self):
        """
        Draw the map of the earthquake if intensity have been calculated.
        """
        if self._eq._expected_intensity is None:
            raise RuntimeError("Intensity have not been calculated yet.")
        if self.fig is None:
            self.init_figure()
        # map boundary
        zoom = 1  # TODO: change zoom according to magnitude
        mid_lon, mid_lat = (TAIWAN_CENTER.lon + self._eq.lon) / 2, (TAIWAN_CENTER.lat + self._eq.lat) / 2
        lon_boundary, lat_boundary = 1.6 * zoom, 2.4 * zoom
        min_lon, max_lon = mid_lon - lon_boundary, mid_lon + lon_boundary
        min_lat, max_lat = mid_lat - lat_boundary, mid_lat + lat_boundary
        self.ax.set_xlim(min_lon, max_lon)
        self.ax.set_ylim(min_lat, max_lat)
        TOWN_DATA.plot(ax=self.ax, facecolor="lightgrey", edgecolor="black", linewidth=0.22 / zoom)
        # group geodata by quake intensity
        region_patch: defaultdict[int, list[pd.Series | pd.DataFrame]] = defaultdict(list)
        for code, region in self._eq._expected_intensity.items():
            if region.intensity.value > 0:
                region_patch[region.intensity.value].append(TOWN_RANGE[code])
        # combine geodata and plot them
        for intensity, gdfs in region_patch.items():
            combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
            combined_gdf["geometry"] = combined_gdf.buffer(0.001)
            gdf_merged = gpd.GeoDataFrame(geometry=[combined_gdf.unary_union])
            gdf_merged.plot(ax=self.ax, color=INTENSITY_COLOR[intensity], edgecolor=None)

        COUNTRY_DATA.plot(ax=self.ax, edgecolor="black", facecolor="none", linewidth=0.64 / zoom)
        # draw epicenter
        self.ax.scatter(
            self._eq.lon,
            self._eq.lat,
            marker="x",
            color="red",
            s=160 / zoom,
            linewidths=2.5 / zoom,
        )
        # add legend
        if self._eq.lon > TAIWAN_CENTER.lon:
            x = 1
            align = 0.8
        else:
            x = 0
            align = 0.2
        self.ax.add_artist(
            AnnotationBbox(
                OffsetImage(legend_img, zoom=0.5),
                (x, 0),
                xycoords="axes fraction",
                boxcoords="axes fraction",
                box_alignment=(align, 0.2),
                frameon=False,
            )
        )
        self._drawn = True

    def draw_wave(self, time: float, waves: str = "all"):
        """
        Draw the P and S wave if possible.

        :param time: the travel time in seconds of the wave to draw
        :type time: float
        :param waves: type of the wave to draw, can be `P`, `S` or `all` (case-insensitive), defaults to `all`
        :type waves: str
        """
        if not self._drawn:
            warnings.warn("Map have not been drawn yet, background will be empty.")

        waves = waves.lower()
        if waves == "all":
            waves = "ps"

        p_dis, s_dis = self._eq._model.get_arrival_distance(time)

        if "p" in waves:
            if self.p_wave is not None:
                self.p_wave.remove()
            self.p_wave = plt.Circle(
                (self._eq.lon, self._eq.lat),
                p_dis,
                color=P_WAVE_COLOR,
                fill=False,
                linewidth=1.5,
            )
            self.ax.add_patch(self.p_wave)

        if "s" in waves:
            if self.s_wave is not None:
                self.s_wave.remove()
            self.s_wave = plt.Circle(
                (self._eq.lon, self._eq.lat),
                s_dis,
                color=S_WAVE_COLOR,
                fill=False,
                linewidth=1.5,
            )
            self.ax.add_patch(self.s_wave)

    def save(self):
        if self.fig is None:
            raise RuntimeError("Map have not been initialized yet.")
        if not self._drawn:
            warnings.warn("Map have not been drawn yet, it will be empty.")

        _map = io.BytesIO()
        self.fig.savefig(_map, format="png", bbox_inches="tight")
        _map.seek(0)
        self._image = _map
        return self._image
