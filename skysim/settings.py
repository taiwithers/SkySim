"""Setup functionality for SkySim. Includes both methods for parsing a
configuration TOML, and converting that data in `Settings` (and friends)
objects.
"""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

import tomllib
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from functools import cached_property
from pathlib import Path
from typing import Any, ForwardRef, Optional, Self  # pylint: disable=unused-import
from zoneinfo import ZoneInfo

import numpy as np
from astropy import units as u
from astropy.coordinates import ICRS, AltAz, Angle, EarthLocation, SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from astropy.time import Time
from astropy.wcs import WCS
from matplotlib.colors import LinearSegmentedColormap
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    ValidationError,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from timezonefinder import TimezoneFinder

from skysim.colours import InputColour, RGBTuple, convert_colour
from skysim.utils import FloatArray, IntArray, get_tempfile_path

# Type Aliases


type ConfigValue = str | date | time | int | float | dict[str, InputColour] | dict[
    int | float, int
] | list[int | float]
type ConfigMapping = Mapping[str, ConfigValue]
type TOMLConfig = dict[  # pylint: disable=invalid-name
    str, dict[str, ConfigValue | dict[str, ConfigValue]]
]
type SettingsPair = tuple["ImageSettings", "PlotSettings"]


# Constants


DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.toml"

DATACLASS_CONFIG = ConfigDict(
    arbitrary_types_allowed=True,
    extra="forbid",
    frozen=True,
)

AIRY_DISK_RADIUS = 23 * u.arcmin / 2
"""How far light from an object should spread. Based on the SIMBAD image of Vega."""

MAXIMUM_LIGHT_SPREAD = 10
"""Calculate the spread of light from an object out to this many standard deviations."""


# Classes


class Settings(BaseModel):  # type: ignore[misc]
    """Base class to interpret often-used configuration values. The `Settings`
    class should never be used or passed directly, but instead should be created
    only for the purpose of then calling `.get_image_settings()` and
    `.get_plot_settings()`.
    """

    model_config = DATACLASS_CONFIG

    # Stored on initialization
    input_location: str | list[float]
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
        cls, angular: u.Quantity["angle"]  # type: ignore[type-arg, name-defined]
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
                "Frequency of snapshots (observation.interval) cannot be longer than "
                "observation.duration."
            )
        return self

    # Derived and stored
    @computed_field()
    @cached_property
    def frames(self) -> PositiveInt:
        """
        Calculates number of frames for movie/observations to take.

        Returns
        -------
        PositiveInt
            Number of frames.
        """
        if self.snapshot_frequency.total_seconds() > 0:
            return int(self.duration / self.snapshot_frequency)
        return 1

    @computed_field()
    @cached_property
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
            return EarthLocation.of_address(self.input_location)
        except NameResolveError as e:
            if "connection" in e.args[0]:
                raise ConnectionError(e.args[0].replace("address", "location")) from e
            raise ValueError(e.args[0].replace("address", "location")) from e

    @computed_field()
    @cached_property
    def timezone(self) -> ZoneInfo:
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
        if tzname is None:
            raise ValueError(  # TODO: add test for this error
                f"Cannot determine timezone for {lat}, {lon} ({self.input_location})"
            )

        return ZoneInfo(tzname)

    @computed_field()
    @cached_property
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
    @cached_property
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
    @cached_property
    def degrees_per_pixel(self) -> u.Quantity["angle"]:  # type: ignore[type-arg, name-defined]
        """
        Calculates the number of degrees spanned by each pixel in the resulting image.

        Returns
        -------
        u.Quantity[angle]
            Degrees per pixel (pixel considered unitless).
        """
        return (self.field_of_view / self.image_pixels).to(u.deg)

    @computed_field()
    @cached_property
    def local_datetimes(self) -> list[datetime]:
        """Observation snapshot times as timezone-aware python times.

        Returns
        -------
        list[time]
            List of observation times.
        """
        utc = [
            t.to_datetime().replace(tzinfo=ZoneInfo("UTC"))
            for t in self.observation_times
        ]
        return [u.astimezone(tz=self.timezone) for u in utc]

    @computed_field()
    @cached_property
    def wcs_objects(self) -> list[WCS]:
        """WCS objects for each timestep.

        Returns
        -------
        list[WCS]
            WCS objects for each timestep.
        """
        wcs_by_frame = []
        for radec in self.observation_radec:
            wcs = WCS(naxis=2)
            wcs.wcs.crpix = [self.image_pixels / 2] * 2
            wcs.wcs.cdelt = [self.degrees_per_pixel.value, self.degrees_per_pixel.value]
            wcs.wcs.crval = [radec.ra.value, radec.dec.value]
            wcs.wcs.ctype = ["RA", "DEC"]
            wcs.wcs.cunit = [u.deg, u.deg]
            wcs_by_frame.append(wcs)
        return wcs_by_frame

    def __str__(self: "Settings") -> str:
        result = ""
        for k, v in self.model_dump().items():
            v = str(v).replace("\n", "\n\t")
            result += f"{k}: {v}\n"
        return result[:-1]

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

    model_config = DATACLASS_CONFIG

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
    def _convert_colour_dict(  # type: ignore[misc]
        cls, colour_dict: dict[str, Any]
    ) -> dict[str, RGBTuple]:
        return {key: convert_colour(value) for key, value in colour_dict.items()}

    @field_validator("colour_values", mode="before")
    @classmethod
    def _convert_colour_list(  # type: ignore[misc]
        cls, colour_list: list[Any]
    ) -> list[RGBTuple]:
        return [convert_colour(value) for value in colour_list]

    # Derived and stored
    @computed_field()
    @cached_property
    def maximum_magnitude(self) -> float:
        """The highest magnitude that will ever be visible in the image.

        Returns
        -------
        float
            Magnitude.
        """
        return max(self.magnitude_values)

    @computed_field()
    @cached_property
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
    @cached_property
    def magnitude_mapping(self) -> FloatArray:
        """Interpolate between the magnitude-time mappings indicated by
        `magnitude_values` and `magnitude_time_indices` to generate an addressable
        mapping.

        Returns
        -------
        FloatArray
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
        return np.interp(day_percentages, magnitude_day_percentage, magnitude_by_time)

    @computed_field()
    @cached_property
    def light_spread_stddev(self) -> PositiveFloat:
        """Standard deviation for the Gaussian which defines the spread of starlight.

        Returns
        -------
        PositiveFloat
            Standard deviation.
        """
        airy_disk_pixels = AIRY_DISK_RADIUS.to(u.deg) / self.degrees_per_pixel
        airy_disk_pixels = airy_disk_pixels.decompose()

        # assume the airy disk is at 3x standard deviation of the Gaussian
        std_dev = airy_disk_pixels / 3

        # standard deviation is "diameter" whilst airy is "radius"
        std_dev *= 2

        return float(std_dev)

    @computed_field()
    @cached_property
    def area_mesh(self) -> IntArray:
        """Create a mesh of indices that spread out from a central point.

        Returns
        -------
        IntArray
            (2, X, X) array.
        """
        maximum_radius = np.ceil(
            MAXIMUM_LIGHT_SPREAD * self.light_spread_stddev
        ).astype(int)

        radius_vector = np.arange(-maximum_radius, maximum_radius + 1)

        # mesh of points which will map to the region around the star
        return np.array(np.meshgrid(radius_vector, radius_vector))

    @computed_field()
    @cached_property
    def brightness_scale_mesh(self) -> FloatArray:
        """Create a mesh of scaling factors that will dictate how a star's light
        falls off with distance.

        Returns
        -------
        FloatArray
            2D mesh of [0,1] values.
        """

        # radius measurement at each mesh point
        radial_distance = np.sqrt(self.area_mesh[0] ** 2 + self.area_mesh[1] ** 2)

        unique_radii = np.unique(radial_distance)

        # all of the locations where each unique radius is found
        radius_locations = []
        for r in unique_radii:
            locations = np.array(np.where(radial_distance == r)).T
            radius_locations.append(locations)

        mesh = np.zeros_like(self.area_mesh[0])  # instantiate brightness_scale_mesh

        for r, p in zip(unique_radii, radius_locations):
            brightness_scale = self.brightness_gaussian(r)
            # TODO: remove this loop by using a smarter numpy-based way to store
            # radius_locations entries
            for x, y in p:
                mesh[y, x] = brightness_scale

        return mesh

    def brightness_gaussian(self, radius: NonNegativeFloat) -> NonNegativeFloat:
        """Calculate how much light is observed from a star at some radius away
        from it.

        Parameters
        ----------
        radius : NonNegativeFloat
            Distance in pixels.

        Returns
        -------
        NonNegativeFloat
            Scaling factor for brightness.
        """
        return np.exp(-(radius**2) / (self.light_spread_stddev**2))


class PlotSettings(Settings):  # type: ignore[misc]
    """`Settings` subclass to hold values used when generating the final plot
    Additionally contains a copy of all attributes belonging to the `Settings` instance
    it inherits from.
    """

    model_config = DATACLASS_CONFIG

    # Stored on initialization
    fps: NonNegativeFloat
    """Frames per second of the GIF/video generated. Zero if there is only one
    frame."""

    filename: Path
    """Location to save the plot."""

    figure_size: tuple[PositiveFloat, PositiveFloat]
    """Size of the figure in inches to pass to `matplotlib`."""

    dpi: PositiveInt
    """Dots per inch, passed to `matplotlib`."""

    @computed_field()
    @cached_property
    def observation_info(self) -> str:
        """Generate a string containing information about the observation for the plot.
        Only contains information which is constant throughout all snapshots.

        Returns
        -------
        str
            Formatted string.
        """
        altitude = angle_to_dms(self.altitude_angle)
        azimuth = angle_to_dms(self.azimuth_angle)
        fov = angle_to_dms(self.field_of_view)
        return (
            f"{self.input_location}\n Altitude: {altitude}, "
            f"Azimuth: {azimuth}, FOV: {fov}"
        )

    @computed_field
    @cached_property
    def datetime_strings(self) -> list[str]:
        """Printable observation times.

        Returns
        -------
        list[str]
            List of strings for each time.
        """
        if (self.start_time.second == 0) and divmod(
            self.snapshot_frequency.total_seconds(), 60
        )[1] == 0:
            fmt_string = "%Y-%m-%d %H:%M %Z"
        else:
            fmt_string = "%Y-%m-%d %X %Z"

        return [i.strftime(fmt_string) for i in self.local_datetimes]

    @computed_field
    @cached_property
    def tempfile_path(self) -> Path:
        """Path to store video frame files.

        Returns
        -------
        Path
            Directory.
        """
        return self.filename.parent / "SkySimFiles"

    @computed_field
    @cached_property
    def tempfile_zfill(self) -> int:
        """How much zero-padding to use when writing the video frame filenames.

        Returns
        -------
        int
            Number of digits.
        """
        return np.ceil(np.log10(self.frames)).astype(int)

    @field_validator("filename", mode="after")
    @classmethod
    def check_parent_directory_exists(cls, filename: Path) -> Path:
        """Raise an error if the directory in which to save the image doesn't exist.

        Parameters
        ----------
        filename : Path
            Location to save image.

        Returns
        -------
        Path :
            Same as input.

        Raises
        ------
        ValueError
            Raised if parent directory does not exist.
        """

        if not filename.parent.exists():
            raise ValueError(
                f"Cannot save result '{filename.resolve()}' because parent directory "
                f"'{filename.parent.resolve()}' does not exist."
            )
        return filename.resolve()

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
            Pydantic `ValidationInfo` object allowing access to the other
            already-validated fields.

        Returns
        -------
        NonNegativeFloat
            Validated fps.

        Raises
        ------
        ValueError
            Raised if `fps` is given as zero but the observation `duration` implies
            there should be multiple frames.
        """
        if info.data["duration"].total_seconds() == 0:
            return 0
        if input_fps == 0:
            raise ValueError(
                f"Non-zero duration ({info.data['duration']}) implies the "
                "creation of a movie, but the given fps was zero."
            )
        return input_fps


# Methods


## Top-Level Settings Methods


def confirm_config_file(input_config_path: str) -> Path:
    """Pre-validate the existence of a config file.

    Parameters
    ----------
    input_config_path : str
        Argument passed on command line.

    Returns
    -------
    Path
        Given config file path (if any).

    Raises
    ------
    ValueError
        Raised if
        - Path given does not exist.
        - Path leads to a non-file object.
        - Path does not have a ".toml" extension.
    """

    config_path = Path(input_config_path).resolve()

    if not config_path.exists():
        raise ValueError(f"{config_path} does not exist.")
    if not config_path.is_file():
        raise ValueError(f"{config_path} is not a file.")
    if config_path.suffix != ".toml":
        raise ValueError(f"{config_path} does not have a '.toml' extension.")

    return config_path


def load_from_toml(
    filename: Path, return_settings: bool = False
) -> Settings | SettingsPair:
    """Load configuration options from a TOML file and parse them into `Settings`
    objects.

    Parameters
    ----------
    filename : str
        Location of the configuration file.
    return_settings : bool, optional
        Whether to return the Settings object (true) or ImageSettings and
        PlotSettings objects (false). Default false.

    Returns
    -------
    tuple[ImageSettings, PlotSettings]
        `Settings` objects generated from the configuration.
    """

    settings_config, image_config, plot_config = toml_to_dicts(filename)

    try:
        settings = Settings(**settings_config)

        if return_settings:
            return settings

        image_settings = settings.get_image_settings(**image_config)
        plot_settings = settings.get_plot_settings(**plot_config)

        return image_settings, plot_settings

    except ValidationError as e:
        # pydantic does a lot of wrapping around their errors...
        original_error = e.errors()[0]
        error_message = original_error["msg"]  # "Value error, [original message]"

        if original_error["type"] == "value_error":  # explicitly raised in a validator
            skip_point = "error, "
            index = error_message.index(skip_point) + len(skip_point)
            new_message = error_message[index:]

        else:  # probaby a type coercion error listed in
            # https://docs.pydantic.dev/2.10/errors/validation_errors/
            bad_dict_key = original_error["loc"][0]
            bad_dict_value = original_error["input"]
            new_message = (
                f"Error processing '{bad_dict_value}' into {bad_dict_key}. "
                f"{error_message}."
            )

        raise ValueError(new_message) from e


def check_for_overwrite(plot_settings: PlotSettings) -> Path | None:
    """Check if SkySim will overwrite any existing files.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.

    Returns
    -------
    Path|None
        Returns either the first path that will be overwritten, or None.
    """
    if plot_settings.filename.exists():
        return plot_settings.filename

    if plot_settings.frames > 1:
        for i in range(plot_settings.frames):
            tempfile_path = get_tempfile_path(plot_settings, i)
            if tempfile_path.exists():
                return tempfile_path

    return None


## Helper Methods


def toml_to_dicts(
    filename: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Read the configuration file and combine it with the default configuration
    to get dictionaries of values which can be used for the various `Settings` classes.

    Parameters
    ----------
    filename : Path
        Path the the toml config file.

    Returns
    -------
    tuple[ConfigMapping]
        Dictionary for `Settings`, `ImageSettings`, and `PlotSettings`.
    """
    with filename.open(mode="rb") as opened:
        try:
            toml_config = tomllib.load(opened)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Error reading config file. {e.args[0]}.") from e

    check_mandatory_toml_keys(toml_config)

    with DEFAULT_CONFIG_PATH.open(mode="rb") as default:
        default_config = tomllib.load(default)

    load_or_default = lambda toml_key, default_key=None: get_config_option(
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
        "image_pixels": load_or_default("image.pixels"),
        "duration": time_to_timedelta(
            load_or_default("observation.duration")  # type: ignore[arg-type]
        ),
        "snapshot_frequency": time_to_timedelta(
            load_or_default("observation.interval")  # type: ignore[arg-type]
        ),
    }

    image_config = {
        k: load_or_default(f"image.{v}", default_key=f"image.{v}")
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
        "fps": load_or_default("image.fps"),
        "dpi": load_or_default("image.dpi"),
        "figure_size": (
            load_or_default("image.width"),
            load_or_default("image.height"),
        ),
    }

    return settings_config, image_config, plot_config


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
    return subdictionary[keys[-1]]


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
        value = access_nested_dictionary(dictionary, split_nested_key(full_key))
        assert len(str(value)) > 0
        return True
    except (KeyError, AssertionError):
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


def parse_angle_dict(
    dictionary: dict[str, int | float],
) -> u.Quantity["angle"]:  # type: ignore[type-arg, name-defined]
    """Convert a dictionary of the form {degrees:X, arcminutes:Y, arcseconds:Z}
    to a single Quantity.

    Parameters
    ----------
    dictionary : dict[str,int|float]
        Dictionary potentially containing angular information.

    Returns
    -------
    u.Quantity (angle)
        Combined angle.
    """
    total_angle = 0 * u.deg

    for key in ["degrees", "arcminutes", "arcseconds"]:
        value = dictionary.get(key, 0)
        try:
            float_value = float(value)
        except ValueError as e:
            raise ValueError(
                f"Could not convert angular value {key}={value} to a float."
            ) from e

        total_angle += float_value * u.Unit(key[:-1])

    return total_angle


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
    """Access a config value from the TOML config provided, and if not present, search
    the provded default config.

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


def angle_to_dms(angle: u.Quantity["angle"]) -> str:  # type: ignore[type-arg,name-defined]
    """Convert a astropy angle to a pretty-printed string.

    Parameters
    ----------
    angle : u.Quantity[angle]
        The angle quantity to format.

    Returns
    -------
    str
        Latex-formatted string.
    """
    arcseconds = angle.to(u.arcsec).value

    has_seconds = divmod(arcseconds, 60)[1] != 0
    has_minutes = divmod(arcseconds, 3600)[1] != 0

    if has_seconds:
        fields = 3
    elif has_minutes:
        fields = 2
    else:
        fields = 1

    ap_angle = Angle(angle)
    return ap_angle.to_string(fields=fields, format="latex")
