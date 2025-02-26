# from pydantic import BaseModel
from datetime import date, datetime, time, timedelta
from typing import Any, ForwardRef
from zoneinfo import ZoneInfo

import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from matplotlib.colors import LinearSegmentedColormap
from numpy.typing import NDArray
from timezonefinder import TimezoneFinder

######## Input handling
# read input from TOML
# CLI arg for TOML filename


class Settings:
    """
    Store config values and derived information
    """

    # Stored on initialization
    input_location: str
    field_of_view: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    altitude_angle: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    azimuth_angle: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    image_pixels: int

    # Derived and stored
    degrees_per_pixel: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    obs_time_values: Time
    ra_dec_values: SkyCoord
    earth_location: EarthLocation
    timezone: ZoneInfo
    frames: int

    def __init__(
        self,
        input_location: str,
        field_of_view: u.Quantity["angle"],  # type: ignore[type-arg, name-defined]
        altitude_angle: u.Quantity["angle"],  # type: ignore[type-arg, name-defined]
        azimuth_angle: u.Quantity["angle"],  # type: ignore[type-arg, name-defined]
        image_pixels: int,
        start_date: date,
        start_time: time,
        snapshot_frequency: timedelta,
        duration: timedelta,
    ) -> None:
        self.input_location = input_location
        self.field_of_view = field_of_view
        self.altitude_angle = altitude_angle
        self.azimuth_angle = azimuth_angle
        self.image_pixels = image_pixels

        self.frames = int(duration / snapshot_frequency)

        self.get_earth_location()
        self.get_timezone()
        self.get_obs_time_values(start_date, start_time, snapshot_frequency)

        self.get_obs_ra_dec()
        self.get_degrees_per_pixel()

        return

    def __str__(self) -> str:
        return str(vars(self))

    def get_obs_time_values(
        self, start_date: date, start_time: time, snapshot_frequency: timedelta
    ) -> None:
        start_datetime = datetime(
            year=start_date.year,
            month=start_date.month,
            day=start_date.day,
            hour=start_time.hour,
            minute=start_time.minute,
            second=start_time.second,
            microsecond=start_time.microsecond,
            tzinfo=self.timezone,
        )
        self.obs_time_values = Time(
            [start_datetime + (snapshot_frequency * i) for i in range(self.frames)]
        )
        return

    def get_earth_location(self) -> None:
        try:
            earth_location = EarthLocation.of_address(self.input_location)
        except:
            raise NotImplementedError

        self.earth_location = earth_location
        return

    def get_obs_ra_dec(self) -> None:
        earth_frame = AltAz(
            obstime=self.obs_time_values,
            az=self.azimuth_angle,
            alt=self.altitude_angle,
            location=self.earth_location,
        )
        self.ra_dec_values = SkyCoord(earth_frame.transform_to(ICRS()))
        return

    def get_degrees_per_pixel(self) -> None:
        self.degrees_per_pixel = (self.field_of_view / self.image_pixels).to(u.deg)
        return

    def get_timezone(self) -> None:
        lat, lon = [
            l.to(u.deg).value
            for l in [self.earth_location.lat, self.earth_location.lon]
        ]
        tf = TimezoneFinder()
        tzname = tf.timezone_at(lat=lat, lng=lon)
        if isinstance(tzname, str):
            self.timezone = ZoneInfo(tzname)
        elif tzname is None:
            raise NotImplementedError
        return

    def passthrough_settings(
        self, subclass_instance: "ImageSettings | PlotSettings"
    ) -> None:
        for name, value in vars(self).items():
            setattr(subclass_instance, name, value)

    def get_image_settings(self, *args: Any) -> "ImageSettings":
        return ImageSettings(self, *args)

    def get_plot_settings(self, *args: Any) -> "PlotSettings":
        return PlotSettings(self, *args)


class ImageSettings(Settings):
    # Stored on initialization
    object_colours: dict[
        str, tuple[float, float, float]
    ]  # same as colour_values for values

    # Derived and stored
    colour_mapping: LinearSegmentedColormap
    magnitude_mapping: NDArray[np.float64]

    def __init__(
        self,
        settings: Settings,
        object_colours: dict[str, tuple[float, float, float]],
        colour_values: list[str],
        colour_time_indices: dict[float | int, int],
        magnitude_values: list[float | int],
        magnitude_time_indices: dict[float | int, int],
    ) -> None:
        self.object_colours = object_colours

        settings.passthrough_settings(self)
        self.get_colour_mapping(colour_values, colour_time_indices)
        self.get_magnitude_mapping(magnitude_values, magnitude_time_indices)

        return

    def get_colour_mapping(
        self,
        colour_values: list[
            str
        ],  # matplotlib also accepts things like rbga tuples, not sure how to annotate that
        colour_time_indices: dict[float | int, int],
    ) -> None:
        colour_by_time = [
            (hour / 24, colour_values[index])
            for hour, index in colour_time_indices.items()
        ]
        self.colour_mapping = LinearSegmentedColormap.from_list("sky", colour_by_time)
        return

    def get_magnitude_mapping(
        self,
        magnitude_values: list[float | int],
        magnitude_time_indices: dict[float | int, int],
    ) -> None:
        magnitude_day_percentage = [hour / 24 for hour in magnitude_time_indices.keys()]
        magnitude_by_time = [
            magnitude_values[index] for index in magnitude_time_indices.values()
        ]
        day_percentages = np.linspace(0, 1, 24 * 60 * 60)
        self.magnitude_mapping = np.interp(
            day_percentages, magnitude_day_percentage, magnitude_by_time
        )
        return


class PlotSettings(Settings):
    # Stored on initialization
    fps: int | float
    filename: str
    figure_size: tuple[int | float, int | float]
    dpi: int

    # Derived and stored
    obs_info: str

    def __init__(
        self,
        settings: Settings,
        fps: int | float,
        filename: str,
        figure_size: tuple[int | float, int | float],
        dpi: int,
    ) -> None:
        self.fps = fps
        self.filename = filename
        self.figure_size = figure_size
        self.dpi = dpi

        settings.passthrough_settings(self)
        self.get_obs_info()
        return

    def get_obs_info(self) -> None:
        altitude = self.altitude_angle.to_string(format="latex")
        azimuth = self.azimuth_angle.to_string(format="latex")
        fov = self.field_of_view.to_string(format="latex")
        self.obs_info = f"{self.input_location}\nAltitude: {altitude}, Azimuth: {azimuth}, FOV: {fov}"
        return


######## Worker Functions


# def get_star_table(settings, obs_time, obs_radius, obs_ra_dec):
#     return


# def get_planet_table(settings, obs_time, obs_frame):
#     return


# def get_maximum_magnitude(image_settings, magnitude_values, obs_time, key_times):
#     return


# def get_visible_objects(
#     settings, maximum_magnitude, planet_table, star_table, obs_radius, obs_ra_dec
# ):
#     return


# def get_empty_image(image_settings, frames, image_pixels):
#     return


# def get_background_blue(image_settings, blue_values, obs_time):
#     return


# def get_background_image(background_blue, empty_image):
#     return


# def get_std_dev(settings, degrees_per_pixel):
#     return


# def get_filled_image(
#     image_settings, object_colours, std_dev, visible_objects, background_image
# ):
#     return


# ########


# def get_wcs_object(image_settings, image_pixels, degrees_per_pixel, ra_dec):
#     return


# def get_printable_time(settings, obs_time):
#     return


# def make_still_image(
#     image_settings, filled_image, wcs, obs_info, printable_time, filename, figsize, dpi
# ):
#     return


# def make_gif(
#     image_settings,
#     filled_image,
#     wcs_by_time,
#     obs_info,
#     printable_time_by_time,
#     fps,
#     filename,
#     figsize,
#     dpi,
# ):
#     return
