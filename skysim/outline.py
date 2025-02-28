"""
Initial outline for SkySim
"""

import tomllib
from collections.abc import Collection, Mapping
from datetime import date, datetime, time, timedelta
from typing import Any, ForwardRef, Optional, cast  # pylint: disable=unused-import
from zoneinfo import ZoneInfo

import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from numpy.typing import NDArray
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic.dataclasses import dataclass
from timezonefinder import TimezoneFinder
from typing_extensions import Annotated, Self

######## Input handling
# read input from TOML
# CLI arg for TOML filename


type RGBTuple = tuple[float, float, float]
type InputColour = list[float | int] | str
type ConfigValue = str | date | time | int | float | dict[str, InputColour] | dict[
    int | float, int
] | list[int | float]
type ConfigMapping = Mapping[str, ConfigValue]
type TOMLConfig = dict[str, dict[str, ConfigValue | dict[str, ConfigValue]]]

dataclass_config = ConfigDict(
    arbitrary_types_allowed=True,
    extra="forbid",
    frozen=True,
)


@dataclass
class RGB:  # type: ignore[misc]
    original: Any

    @computed_field()
    @property
    def rgb(self) -> RGBTuple:
        if (
            isinstance(self.original, Collection)
            and not isinstance(self.original, str)
            and (len(self.original) in (3, 4))
            and any(i > 1 for i in self.original)
        ):
            self.original = tuple(i / 255 for i in self.original)
        return to_rgb(self.original)  # pyright: ignore


def convert_colour(colour: Any) -> RGBTuple:
    return RGB(colour).rgb


class Settings(BaseModel):  # type: ignore[misc]
    model_config = dataclass_config

    # Stored on initialization
    input_location: str
    field_of_view: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    altitude_angle: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    azimuth_angle: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    image_pixels: PositiveInt

    # Used to instantiate others, and stored, but hidden
    start_date: date = Field(repr=False)
    snapshot_frequency: timedelta = Field(repr=False)
    duration: timedelta = Field(repr=False)  # init_var=True)
    start_time: time = Field(repr=False)

    # Derived and stored
    @computed_field()
    @property
    def frames(self) -> NonNegativeInt:
        if self.snapshot_frequency.total_seconds() > 0:
            return int(self.duration / self.snapshot_frequency)
        return 0

    @computed_field()
    @property
    def earth_location(self) -> EarthLocation:
        try:
            return EarthLocation.of_address(self.input_location)  # type: ignore[no-any-return]
        except:
            raise NotImplementedError

    @computed_field()
    @property
    def timezone(self) -> ZoneInfo:  # pyright: ignore
        lat, lon = [
            l.to(u.deg).value
            for l in [self.earth_location.lat, self.earth_location.lon]
        ]
        tf = TimezoneFinder()
        tzname = tf.timezone_at(lat=lat, lng=lon)
        if isinstance(tzname, str):
            return ZoneInfo(tzname)
        elif tzname is None:
            raise NotImplementedError

    @computed_field()
    @property
    def observation_times(self) -> Time:
        start_datetime = datetime(
            year=self.start_date.year,
            month=self.start_date.month,
            day=self.start_date.day,
            hour=self.start_time.hour,
            minute=self.start_time.minute,
            second=self.start_time.second,
            microsecond=self.start_time.microsecond,
            tzinfo=self.timezone,
        )
        return Time(
            [start_datetime + (self.snapshot_frequency * i) for i in range(self.frames)]
        )

    @computed_field()
    @property
    def observation_radec(self) -> SkyCoord:
        earth_frame = AltAz(
            obstime=self.observation_times,
            az=self.azimuth_angle,
            alt=self.altitude_angle,
            location=self.earth_location,
        )
        return SkyCoord(earth_frame.transform_to(ICRS()))

    @computed_field()
    @property
    def degrees_per_pixel(self) -> u.Quantity["angle"]:  # type: ignore[type-arg, name-defined]
        return (self.field_of_view / self.image_pixels).to(u.deg)  # type: ignore[no-any-return]

    def get_image_settings(self: "Settings", **kwargs: Any) -> "ImageSettings":
        return ImageSettings(**vars(self), **kwargs)

    def get_plot_settings(self: "Settings", **kwargs: Any) -> "PlotSettings":
        return PlotSettings(**vars(self), **kwargs)


class ImageSettings(Settings):  # type: ignore[misc]
    model_config = dataclass_config

    # Stored on initialization
    object_colours: dict[str, Any] = Field()

    # Used to instantiate others, but not stored
    # settings: Settings = Field(repr=False)
    colour_values: list[Any] = Field(repr=False)
    colour_time_indices: dict[float | int, int] = Field(repr=False)
    magnitude_values: list[float | int] = Field(repr=False)
    magnitude_time_indices: dict[float | int, int] = Field(repr=False)

    @field_validator("object_colours", mode="before")
    @classmethod
    def convert_colour_dict(cls, colour_dict: dict[str, Any]) -> dict[str, RGBTuple]:  # type: ignore[misc]
        return {key: convert_colour(value) for key, value in colour_dict.items()}

    @field_validator("colour_values", mode="before")
    @classmethod
    def convert_colour_list(cls, colour_list: list[Any]) -> list[RGBTuple]:  # type: ignore[misc]
        return [convert_colour(value) for value in colour_list]

    # Derived and stored
    @computed_field()
    @property
    def colour_mapping(self) -> LinearSegmentedColormap:
        colour_by_time = [
            (hour / 24, self.colour_values[index])
            for hour, index in self.colour_time_indices.items()
        ]
        return LinearSegmentedColormap.from_list("sky", colour_by_time)

    @computed_field()
    @property
    def magnitude_mapping(self) -> NDArray[np.float64]:
        magnitude_day_percentage = [
            hour / 24 for hour in self.magnitude_time_indices.keys()
        ]
        magnitude_by_time = [
            self.magnitude_values[index]
            for index in self.magnitude_time_indices.values()
        ]
        day_percentages = np.linspace(0, 1, 24 * 60 * 60)
        return np.interp(day_percentages, magnitude_day_percentage, magnitude_by_time)  # type: ignore[no-any-return]


class PlotSettings(Settings):  # type: ignore[misc]
    model_config = dataclass_config

    # Stored on initialization
    fps: NonNegativeFloat
    filename: str
    figure_size: tuple[PositiveFloat, PositiveFloat]
    dpi: PositiveInt

    @computed_field()
    @property
    def observation_info(self) -> str:
        altitude = self.altitude_angle.to_string(format="latex")
        azimuth = self.azimuth_angle.to_string(format="latex")
        fov = self.field_of_view.to_string(format="latex")
        return (
            f"{self.input_location}\n Altitude: {altitude}, "
            f"Azimuth: {azimuth} , FOV: {fov}"
        )

    @model_validator(mode="after")
    def validate_fps(self) -> Self:
        if self.duration.total_seconds() == 0:
            self.fps = 0
            return self
        if self.fps == 0:
            raise ValueError(
                f"Non-zero duration ({self.duration}) implies the creation of a GIF, but the given fps was zero."
            )
        return self


def access_nested_dictionary(
    dictionary: TOMLConfig, full_key: str, split_character: str = "."
) -> ConfigValue:
    keys = full_key.split(split_character)
    subdictionary = dictionary.copy()
    for key in keys[:-1]:
        subdictionary = subdictionary[key]  # type: ignore[assignment]
    return subdictionary[keys[-1]]  # type: ignore[return-value]


def check_key_exists(dictionary: TOMLConfig, full_key: str) -> bool:
    try:
        access_nested_dictionary(dictionary, full_key)
        return True
    except KeyError:
        return False


def check_toml_presence(dictionary: TOMLConfig) -> None:
    mandatory_keys = [f"observation.{key}" for key in ("location", "date", "time")] + [
        "image.filename"
    ]

    one_or_more_keys = [
        [
            f"observation.{key}.{unit}"
            for unit in ("degrees", "arcminutes", "arcseconds")
        ]
        for key in ("viewing-radius", "altitude", "azimuth")
    ]

    all_or_none_keys = [
        [f"observation.{key}" for key in ("interval", "duration")],
        [f"image.{key}" for key in ("width", "height")],
    ]
    # check that mandatory keys are provided
    for key in mandatory_keys:
        if not check_key_exists(dictionary, key):
            raise ValueError(f"Required element {key} was not found.")

    # check that one-or-more keys are provided
    for keyset in one_or_more_keys:
        keys_exist = [check_key_exists(dictionary, key) for key in keyset]
        if not any(keys_exist):
            raise ValueError(
                f"One or more of {keyset} must be given, but none were found."
            )

    # all_or_none keys
    for keyset in all_or_none_keys:
        keys_exist = [check_key_exists(dictionary, key) for key in keyset]
        if (not (all(keys_exist))) and any(keys_exist):
            raise ValueError(
                f"Some but not all of the keys {keyset} were given. "
                "These keys must be given all together or not at all."
            )

    return


def parse_angle_dict(
    dictionary: dict[str, int | float],
) -> u.Quantity["angle"]:  # type: ignore[type-arg, name-defined]
    """
    Convert a dictionary of the form {degrees:X, arcminutes:Y, arcseconds:Z}
    to a single Quantity

    Parameters
    ----------
    dictionary : _type_
        _description_
    """

    degrees, arcminutes, arcseconds = (
        dictionary.get(key, 0) * u.Unit(key[:-1])
        for key in ["degrees", "arcminutes", "arcseconds"]
    )
    return degrees + arcminutes + arcseconds  # type: ignore[no-any-return]


def time_to_timedelta(time_object: time) -> timedelta:
    components = {
        key: getattr(time_object, key[:-1])
        for key in ("hours", "minutes", "seconds", "microseconds")
    }
    return timedelta(**components)


def get_config_option(
    toml_dictionary: TOMLConfig,
    toml_key: str,
    default_config: TOMLConfig,
    default_key: Optional[str] = None,
) -> ConfigValue:
    if check_key_exists(toml_dictionary, toml_key):
        return access_nested_dictionary(toml_dictionary, toml_key)
    if default_key is None:
        default_key = toml_key
    return access_nested_dictionary(default_config, default_key)


# TODO: type filename as path (pathlib?)
def load_from_toml(filename: str) -> tuple[ImageSettings, PlotSettings]:
    with open(filename, "rb") as opened:
        toml_config = tomllib.load(opened)

    check_toml_presence(toml_config)

    with open("skysim/default.toml", "rb") as default:
        default_config = tomllib.load(default)

    settings_config = {
        "input_location": toml_config["observation"]["location"],
        "field_of_view": parse_angle_dict(toml_config["observation"]["viewing-radius"]),
        "altitude_angle": parse_angle_dict(toml_config["observation"]["altitude"]),
        "azimuth_angle": parse_angle_dict(toml_config["observation"]["azimuth"]),
        "image_pixels": get_config_option(toml_config, "image.pixels", default_config),
        "duration": time_to_timedelta(toml_config["observation"]["duration"]),
        "snapshot_frequency": time_to_timedelta(toml_config["observation"]["interval"]),
        "start_date": toml_config["observation"]["date"],
        "start_time": toml_config["observation"]["time"],
    }

    image_config = {
        k: get_config_option(toml_config, f"image.{v}", default_config, f"image.{k}")
        for k, v in {
            "object_colours": "object-colours",
            "colour_values": "sky-colours",
            "colour_time_indices": "sky-colours-index-by-time",
            "magnitude_values": "maximum-magnitudes",
            "magnitude_time_indices": "maximum-magnitudes-index-by-time",
        }.items()
    }

    plot_config = {
        "fps": toml_config["image"]["fps"],
        "filename": toml_config["image"]["filename"],
        "figure_size": (toml_config["image"][d] for d in ("width", "height")),
        "dpi": toml_config["image"]["dpi"],
    }

    settings = Settings(**settings_config)
    image_settings = settings.get_image_settings(**image_config)
    plot_settings = settings.get_plot_settings(**plot_config)

    return image_settings, plot_settings


if __name__ == "__main__":
    image_settings, plot_settings = load_from_toml(
        "/home/taiwithers/projects/skysim/skysim/config.toml"
    )
    print(plot_settings)
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
