"""
Initial outline for SkySim.
"""

import tomllib
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import Any, ForwardRef, Optional, Self  # pylint: disable=unused-import
from zoneinfo import ZoneInfo

import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from matplotlib.colors import LinearSegmentedColormap
from numpy.typing import NDArray
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from timezonefinder import TimezoneFinder

from .colours import InputColour, RGBTuple, convert_colour

# TODO: look for tomllib typing

type ConfigValue = str | date | time | int | float | dict[str, InputColour] | dict[
    int | float, int
] | list[int | float]
type ConfigMapping = Mapping[str, ConfigValue]
type TOMLConfig = dict[  # pylint: disable=invalid-name
    str, dict[str, ConfigValue | dict[str, ConfigValue]]
]
type SettingsPair = tuple["ImageSettings", "PlotSettings"]

dataclass_config = ConfigDict(
    arbitrary_types_allowed=True,
    extra="forbid",
    frozen=True,
)


class Settings(BaseModel):  # type: ignore[misc]
    """Base class to interpret often-used configuration values."""

    model_config = dataclass_config

    # Stored on initialization
    input_location: str
    """User-input version of the observing location."""

    field_of_view: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    """Diameter of the area being observed at any time."""

    altitude_angle: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    """Angle of observation (measured from horizon)."""

    azimuth_angle: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
    """Angle of observation (Eastwards from North)."""

    image_pixels: PositiveInt
    """Number of pixels (diameter) for the resulting image."""

    # Used to instantiate others, and stored, but hidden
    start_date: date = Field(repr=False)
    """Starting (local) date of observation."""

    start_time: time = Field(repr=False)
    """Starting (local) time of observation."""

    snapshot_frequency: timedelta = Field(repr=False)
    """How often an observation should be taken - should be given in concert
    with `duration` """

    duration: timedelta = Field(repr=False)
    """How long the total observation should last - should be given in concert
    with `snapshot_frequency`"""

    @field_validator("field_of_view", "altitude_angle", "azimuth_angle", mode="after")
    @classmethod
    def convert_to_deg(
        cls, angular: u.Quantity["angle"]
    ) -> u.Quantity["degree"]:  # type: ignore[type-arg, name-defined]
        # pylint: disable=missing-function-docstring
        return angular.to(u.deg)

    @model_validator(mode="after")
    def compare_timespans(self) -> Self:
        """
        Confirm that the time between snapshots is not greater than the observation
        duration.

        Returns
        -------
        Self
            `Settings` object.

        Raises
        ------
        ValueError
            Raised if the snapshot frequency is greater than the duration.
        """
        if self.snapshot_frequency > self.duration:
            raise ValueError(
                "Frequency of snapshots cannot be longer than the observation duration."
            )
        return self

    # Derived and stored
    @computed_field()
    @property
    def frames(self) -> PositiveInt:
        """
        Calculates number of frames for GIF/observations to take.

        Returns
        -------
        PositiveInt
            Number of frames.
        """
        if self.snapshot_frequency.total_seconds() > 0:
            return int(self.duration / self.snapshot_frequency)
        return 1

    @computed_field()
    @property
    def earth_location(self) -> EarthLocation:
        """
        Looks up where on Earth the user requested the observation be taken from.

        Returns
        -------
        EarthLocation
            Astropy representation of location on Earth.

        Raises
        ------
        NotImplementedError
            Raised if location lookup fails.
        """
        try:
            return EarthLocation.of_address(self.input_location)  # type: ignore[no-any-return]
        except:
            # TODO: location validation
            raise NotImplementedError  # pylint: disable=raise-missing-from

    @computed_field()
    @property
    def timezone(self) -> ZoneInfo:  # pylint: disable=inconsistent-return-statements
        """
        Look up timezone based on Lat/Long.

        Returns
        -------
        ZoneInfo
            Timezone information.

        Raises
        ------
        NotImplementedError
            Raised in the case that the lookup fails.
        """
        lat, lon = [
            l.to(u.deg).value
            for l in [self.earth_location.lat, self.earth_location.lon]
        ]
        tf = TimezoneFinder()
        tzname = tf.timezone_at(lat=lat, lng=lon)
        if isinstance(tzname, str):
            return ZoneInfo(tzname)
        if tzname is None:
            # TODO: timezone validation [remove pylint pragma]
            raise NotImplementedError

    @computed_field()
    @property
    def observation_times(self) -> Time:
        """
        Calculates the times at which to take a snapshot.

        Returns
        -------
        Time
            Astropy representation of one or more times.
        """
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
            [(start_datetime + self.snapshot_frequency * i) for i in range(self.frames)]
        )

    @computed_field()
    @property
    def observation_radec(self) -> SkyCoord:
        """
        Calculates the observed RA/Dec position for each observation snapshot.

        Returns
        -------
        SkyCoord
            Astropy representation of one or more coordinates.
        """
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
        """
        Calculates the number of degrees spanned by each pixel in the resulting image.

        Returns
        -------
        u.Quantity["angle"]
            Degrees per pixel (pixel considered unitless).
        """
        return (self.field_of_view / self.image_pixels).to(u.deg)  # type: ignore[no-any-return]

    def get_image_settings(self: "Settings", **kwargs: Any) -> "ImageSettings":
        """
        Generate an `ImageSettings` object inheriting this object's information.

        Parameters
        ----------
        **kwargs
            Dictionary of arguments to be passed to `ImageSettings`.

        Returns
        -------
        ImageSettings
            Object containing all passed configuration values as well as those from the
            instantiation of this `Settings` object.
        """
        return ImageSettings(**vars(self), **kwargs)

    def get_plot_settings(self: "Settings", **kwargs: Any) -> "PlotSettings":
        """
        Generate an `PlotSettings` object inheriting this object's information.

        Parameters
        ----------
        **kwargs
            Dictionary of arguments to be passed to `PlotSettings`.

        Returns
        -------
        PlotSettings
            Object containing all passed configuration values as well as those from the
            instantiation of this `Settings` object.
        """
        return PlotSettings(**vars(self), **kwargs)


class ImageSettings(Settings):  # type: ignore[misc]
    """`Settings` subclass to hold values used when populating the image array.
    Additionally contains a copy of all attributes belonging to the `Settings` instance
    it inherits from.
    """

    model_config = dataclass_config

    # Stored on initialization
    object_colours: dict[str, RGBTuple] = Field()
    """Mapping between object types, and the colours to use on the image."""

    # Used to instantiate others
    colour_values: list[RGBTuple] = Field(repr=False)
    """List of colours to use to fill out the background."""

    colour_time_indices: dict[float | int, int] = Field(repr=False)
    """Mapping between hour of the day (0-24, float) and the index corresponding
        to the colour in `colour_values` to use at that time."""

    magnitude_values: list[float | int] = Field(repr=False)
    """List of maximum magnitude values, to be used in the same manner as
    `colour_values`."""

    magnitude_time_indices: dict[float | int, int] = Field(repr=False)
    """Same as `colour_time_indices`, except applying to magnitude_values. Need not be
        the same as `colour_time_indices`."""

    @field_validator("object_colours", mode="before")
    @classmethod
    def _convert_colour_dict(cls, colour_dict: dict[str, Any]) -> dict[str, RGBTuple]:  # type: ignore[misc]
        return {key: convert_colour(value) for key, value in colour_dict.items()}

    @field_validator("colour_values", mode="before")
    @classmethod
    def _convert_colour_list(cls, colour_list: list[Any]) -> list[RGBTuple]:  # type: ignore[misc]
        return [convert_colour(value) for value in colour_list]

    # Derived and stored
    @computed_field()
    @property
    def maximum_magnitude(self) -> float:
        """The highest magnitude that will ever be visible in the image.

        Returns
        -------
        float
            Magnitude.
        """
        return max(self.magnitude_values)

    @computed_field()
    @property
    def colour_mapping(self) -> LinearSegmentedColormap:
        """Interpolate between the colour-time mappings indicated by `colour_values` and
        `colour_time_indices` to generate an addressable mapping.

        Returns
        -------
        LinearSegmentedColormap
            Callable object on the interval [0,1] returning a RGBTuple.
        """
        colour_by_time = [
            (hour / 24, self.colour_values[index])
            for hour, index in self.colour_time_indices.items()
        ]
        return LinearSegmentedColormap.from_list("sky", colour_by_time)

    @computed_field()
    @property
    def magnitude_mapping(self) -> NDArray[np.float64]:
        """Interpolate between the magnitude-time mappings indicated by `magnitude_values` and
        `magnitude_time_indices` to generate an addressable mapping.

        Returns
        -------
        NDArray[np.float64]
            Array containing the calculated magnitude value for each second of the day.
        """
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
    """`Settings` subclass to hold values used when generating the final plot
    Additionally contains a copy of all attributes belonging to the `Settings` instance
    it inherits from.
    """

    model_config = dataclass_config

    # Stored on initialization
    fps: NonNegativeFloat
    """Frames per second of the GIF/video generated. Zero if there is only one
    frame."""

    filename: str
    """Location to save the plot."""

    figure_size: tuple[PositiveFloat, PositiveFloat]
    """Size of the figure in inches to pass to `matplotlib`."""

    dpi: PositiveInt
    """Dots per inch, passed to `matplotlib`."""

    @computed_field()
    @property
    def observation_info(self) -> str:
        """Generate a string containing information about the observation for the plot.
        Only contains information which is constant throughout all snapshots.

        Returns
        -------
        str
            Formatted string.
        """
        altitude = self.altitude_angle.to_string(format="latex")
        azimuth = self.azimuth_angle.to_string(format="latex")
        fov = self.field_of_view.to_string(format="latex")
        return (
            f"{self.input_location}\n Altitude: {altitude}, "
            f"Azimuth: {azimuth} , FOV: {fov}"
        )

    @field_validator("fps", mode="after")
    @classmethod
    def validate_fps(
        cls, input_fps: NonNegativeFloat, info: ValidationInfo
    ) -> NonNegativeFloat:
        """Ensure fps conforms to the described requirements.

        Parameters
        ----------
        input_fps : NonNegativeFloat
            Frames per second as input when instantiating the `PlotSettings` object.
        info : ValidationInfo
            Pydantic `ValidationInfo` object allowing access to the other already-validated fields.

        Returns
        -------
        NonNegativeFloat
            Validated fps.

        Raises
        ------
        ValueError
            Raised if `fps` is given as zero but the observation `duration` implies there should be multiple frames.
        """
        if info.data["duration"].total_seconds() == 0:
            return 0
        if input_fps == 0:
            raise ValueError(
                f"Non-zero duration ({info.duration}) implies the creation of a GIF, but the given fps was zero."
            )
        return input_fps


def split_nested_key(full_key: str) -> list[str]:
    # pylint: disable=missing-function-docstring
    return full_key.split(".")


def access_nested_dictionary(
    dictionary: dict[str, Any], keys: list[str]
) -> ConfigValue:
    """Access a value from an arbitrarily nested dictionary via a list of keys.

    Parameters
    ----------
    dictionary : dict[str, Any]
        The top-level dictionary.
    keys : list[str]
        List of dictionary keys.

    Returns
    -------
    ConfigValue
        The accessed value.
    """
    subdictionary = dictionary.copy()
    for key in keys[:-1]:
        subdictionary = subdictionary[key]
    return subdictionary[keys[-1]]  # type: ignore[no-any-return]


def check_key_exists(dictionary: TOMLConfig, full_key: str) -> bool:
    """Check if a key exists within a nested dictionary.

    Parameters
    ----------
    dictionary : TOMLConfig
        The top-level dictionary to check.
    full_key : str
        Potentially nested key.

    Returns
    -------
    bool
        Whether or not the key exists.
    """
    try:
        access_nested_dictionary(dictionary, split_nested_key(full_key))
        return True
    except KeyError:
        return False


def check_mandatory_toml_keys(dictionary: TOMLConfig) -> None:
    """Validate the existence of the required keys in the TOML configuration.

    Parameters
    ----------
    dictionary : TOMLConfig
        Loaded user configuration.

    Raises
    ------
    ValueError
        Raised if:
            - mandatory keys aren't present
            - keys that require at least one of some group aren't present
            - keys that are required in sets are not property provided
    """
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
        if (not all(keys_exist)) and any(keys_exist):
            raise ValueError(
                f"Some but not all of the keys {keyset} were given. "
                "These keys must be given all together or not at all."
            )

    return


def parse_angle_dict(dictionary: dict[str, int | float]) -> u.Quantity["angle"]:  # type: ignore[type-arg, name-defined]
    """Convert a dictionary of the form {degrees:X, arcminutes:Y, arcseconds:Z}
    to a single Quantity.

    Parameters
    ----------
    dictionary : dict[str,int|float]
        Dictionary potentially containing angular information.

    Returns
    -------
    u.Quantity['angle']
        Combined angle.
    """

    degrees, arcminutes, arcseconds = (
        dictionary.get(key, 0) * u.Unit(key[:-1])
        for key in ["degrees", "arcminutes", "arcseconds"]
    )
    return degrees + arcminutes + arcseconds  # type: ignore[no-any-return]


def time_to_timedelta(time_object: time) -> timedelta:
    """Converts a `time` object to a `timedelta`.

    Parameters
    ----------
    time_object : time
        Time as parsed by TOML.

    Returns
    -------
    timedelta
        Timedelta corresponding to the time from midnight to the given time.
    """
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
    """Access a config value from the TOML config provided, and if not present, search the
    provded default config.

    Parameters
    ----------
    toml_dictionary : TOMLConfig
        TOML configuration.
    toml_key : str
        Nested key to access the TOML dictionary with.
    default_config : TOMLConfig
        Default configuration dictionary.
    default_key : Optional[str], optional
        Alternative key to access the default dictionary with, if different from
        `toml_key`, by default None.

    Returns
    -------
    ConfigValue
        Value as located in one of the dictionaries.
    """
    if check_key_exists(toml_dictionary, toml_key):
        return access_nested_dictionary(toml_dictionary, split_nested_key(toml_key))
    if default_key is None:
        default_key = toml_key
    return access_nested_dictionary(default_config, split_nested_key(default_key))


# TODO: type filename as path (pathlib?)
def load_from_toml(filename: str) -> SettingsPair:
    """Load configuration options from a TOML file and parse them into `Settings` objects.

    Parameters
    ----------
    filename : str
        Location of the configuration file.

    Returns
    -------
    tuple[ImageSettings, PlotSettings]
        `Settings` objects generated from the configuration.
    """
    with open(filename, "rb") as opened:
        toml_config = tomllib.load(opened)

    check_mandatory_toml_keys(toml_config)

    with open("skysim/default.toml", "rb") as default:
        default_config = tomllib.load(default)

    load_entry = lambda toml_key, default_key=None: get_config_option(
        toml_config, toml_key, default_config, default_key
    )

    settings_config = {
        # Mandatory
        "input_location": toml_config["observation"]["location"],
        "field_of_view": parse_angle_dict(toml_config["observation"]["viewing-radius"]),
        "altitude_angle": parse_angle_dict(toml_config["observation"]["altitude"]),
        "azimuth_angle": parse_angle_dict(toml_config["observation"]["azimuth"]),
        "start_date": toml_config["observation"]["date"],
        "start_time": toml_config["observation"]["time"],
        # Optional
        "image_pixels": load_entry("image.pixels"),
        "duration": time_to_timedelta(load_entry("observation.duration")),  # type: ignore[arg-type]
        "snapshot_frequency": time_to_timedelta(load_entry("observation.interval")),  # type: ignore[arg-type]
    }

    image_config = {
        k: load_entry(f"image.{v}", default_key=f"image.{v}")
        for k, v in {
            # Optional
            "object_colours": "object-colours",
            "colour_values": "sky-colours",
            "colour_time_indices": "sky-colours-index-by-time",
            "magnitude_values": "maximum-magnitudes",
            "magnitude_time_indices": "maximum-magnitudes-index-by-time",
        }.items()
    }

    plot_config = {
        # Mandatory
        "filename": toml_config["image"]["filename"],
        # Optional
        "fps": load_entry("image.fps"),
        "dpi": load_entry("image.dpi"),
        "figure_size": (load_entry("image.width"), load_entry("image.height")),
    }

    settings = Settings(**settings_config)
    image_settings = settings.get_image_settings(**image_config)
    plot_settings = settings.get_plot_settings(**plot_config)

    return image_settings, plot_settings


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
