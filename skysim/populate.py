"""Create an RGB image matrix of the observation using objects found by
:doc:`skysim.query <query>` and image configuration from an
`~skysim.settings.ImageSettings` object.
"""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

from datetime import datetime, time, timedelta
from multiprocessing import Pool, cpu_count

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable, Row, vstack
from matplotlib.colors import LinearSegmentedColormap
from numpy.typing import ArrayLike
from pydantic import NonNegativeFloat, PositiveInt

from skysim.colours import RGBTuple
from skysim.settings import ImageSettings
from skysim.utils import (
    FloatArray,
    IntArray,
    round_columns,
)

# Constants


MINIMUM_BRIGHTNESS = 0.2
"""Minimum brightness for an object. An object with the highest allowed
magnitude would have this brightness in order to keep it visible against the (0
brightness) backdrop."""


# Methods


## Top-Level Populate Method


def create_image_matrix(
    image_settings: ImageSettings,
    planet_tables: list[QTable],
    star_table: QTable,
    verbose_level: int,
) -> FloatArray:
    """Primary function for the populate module. Creates and fills in the image
    matrix.

    Parameters
    ----------
    image_settings : ImageSettings
        Configuration needed.
    planet_tables : list[astropy.table.QTable]
        Result of planet queries.
    star_table : astropy.table.QTable
        Result of SIMBAD queries.
    verbose_level : int
        How much detail to print.

    Returns
    -------
    FloatArray
        Array of RGB image frames.
    """
    image_matrix = get_empty_image(image_settings.frames, image_settings.image_pixels)

    # fill all the backgrounds
    for i in range(image_settings.frames):
        background_colour = get_timed_background_colour(
            image_settings.colour_mapping, image_settings.local_datetimes[i]
        )
        image_matrix[i] = fill_frame_background(background_colour, image_matrix[i])

    # prepare tables for each frame
    object_tables = [
        prepare_object_table(image_settings, star_table, planet_tables, i)
        for i in range(image_settings.frames)
    ]

    # add in all the objects
    with Pool(cpu_count() - 1) as pool:
        filled_frames = pool.starmap(
            fill_frame_objects,
            [
                (i, image_matrix[i], object_tables[i], image_settings, verbose_level)
                for i in range(image_settings.frames)
                if len(object_tables[i]) > 0
            ],
        )

    # re-sort the frames
    for index, frame in filled_frames:
        image_matrix[index] = frame

    image_matrix = np.moveaxis(image_matrix, 1, -1)  # put the RGB axis at the end

    image_matrix = np.flip(image_matrix, axis=2)  # put the x-axis the right way round

    return image_matrix


## Helper Methods


def get_empty_image(
    frames: PositiveInt,
    image_pixels: PositiveInt,
) -> FloatArray:
    """Initialize an empty image array.

    Parameters
    ----------
    frames : pydantic.PositiveInt
        The number of frames to include.
    image_pixels : pydantic.PositiveInt
        The width/height of the image in pixels.

    Returns
    -------
    FloatArray
        An array of zeros.
    """
    return np.zeros(
        (
            frames,
            3,
            image_pixels,
            image_pixels,
        )
    )


def get_seconds_from_midnight(local_time: time | datetime) -> NonNegativeFloat:
    """Calculate the number of seconds since midnight for some time value.

    Parameters
    ----------
    local_time : datetime.time
        Python time value, can be naive.

    Returns
    -------
    pydantic.NonNegativeFloat
        Number of seconds.
    """
    delta_midnight = timedelta(
        hours=local_time.hour,
        minutes=local_time.minute,
        microseconds=local_time.microsecond,
    )
    return delta_midnight.total_seconds()


def get_timed_background_colour(
    background_colours: LinearSegmentedColormap,
    local_datetime: datetime,
) -> RGBTuple:
    """Get the background colour for the image based on the colour-time mapping.

    Parameters
    ----------
    background_colours : matplotlib.colors.LinearSegmentedColormap
        Colourmap linking floats [0,1] to RGB values.
    local_datetime : datetime.datetime
        Local time of the observation.

    Returns
    -------
    RGBTuple
        Colour corresponding to `local_datetime`.
    """
    day_percentage = get_seconds_from_midnight(local_datetime) / (24 * 60 * 60)

    return background_colours(day_percentage)[:-1]


def get_timed_magnitude(
    magnitude_mapping: FloatArray, local_datetime: datetime
) -> float:
    """Get the maximum magnitude value visible for a current time.

    Parameters
    ----------
    magnitude_mapping : FloatArray
        Array with size [seconds per day] and values [viewable magnitudes].
    local_datetime : datetime.datetime
        Local time of the observation.

    Returns
    -------
    float
        Magnitude value corresponding to `local_datetime`.
    """
    index = int(get_seconds_from_midnight(local_datetime))
    return magnitude_mapping[index]


def fill_frame_background(colour: RGBTuple, frame_matrix: FloatArray) -> FloatArray:
    """Fill an RGB image with a colour.

    Parameters
    ----------
    colour : RGBTuple
        RGB values.
    frame_matrix : FloatArray
        Array with shape (3, X, Y) to be filled.

    Returns
    -------
    FloatArray
        Filled array.
    """
    fake_frame = np.ones_like(frame_matrix).T
    return np.swapaxes(fake_frame * colour, 0, -1)


def filter_objects_brightness(
    maximum_magnitude: float, objects_table: QTable
) -> QTable:
    """Filter a table of objects by the maximum magitude that can be seen.

    Parameters
    ----------
    maximum_magnitude : float
        Highest (inclusive) value for magnitude.
    objects_table : astropy.table.QTable
        Table to be filtered. Should have a "magnitude" column.

    Returns
    -------
    astropy.table.QTable
        Filtered table.
    """
    indices = objects_table["magnitude"] <= maximum_magnitude
    return objects_table[indices]


def filter_objects_fov(
    radec: SkyCoord,
    fov: u.Quantity["angle"],  # type: ignore[type-arg,name-defined]
    objects_table: QTable,
) -> QTable:
    """Filter a table of objects by their distance to a point.

    Parameters
    ----------
    radec : astropy.coordinates.SkyCoord
        Point of observations.
    fov : astropy.units.Quantity[angle]
        Field of view (2x visible radius).
    objects_table : astropy.table.QTable
        Table of objects to be filtered.

    Returns
    -------
    astropy.table.QTable
        Filtered table.
    """

    object_separations = objects_table["skycoord"].separation(radec)

    maximum_separation = (
        fov / 2 * 1.01
    )  # add 1% buffer to capture light from objects near the edge of the frame
    indices = object_separations <= maximum_separation
    return objects_table[indices]


def magnitude_to_flux(magnitude: ArrayLike) -> ArrayLike:
    """Magnitude to flux conversion (relative to some reference value).

    Parameters
    ----------
    magnitude : numpy.typing.ArrayLike
        Apparent magnitude.

    Returns
    -------
    numpy.typing.ArrayLike
        Relative flux.
    """
    return 10 ** (-magnitude / 2.5)  # type: ignore[operator]


def linear_rescale(
    data: ArrayLike, new_min: float = 0, new_max: float = 1
) -> ArrayLike:
    """Generic function to linearly scale data between some minimum and maximum.

    Parameters
    ----------
    data : numpy.typing.ArrayLike
        Data to be scaled.
    new_min : float, optional
        New minimum, by default 0.
    new_max : float, optional
        New maximum, by default 1.

    Returns
    -------
    numpy.typing.ArrayLike
        Scaled data.
    """
    data_min, data_max = np.min(data), np.max(data)
    data_range = data_max - data_min
    if data_range == 0:
        data_range = 1
    new_range = new_max - new_min

    return (data - data_min) * (new_range / data_range) + new_min


def get_scaled_brightness(object_table: QTable) -> QTable:
    """Add a new column to `object_table` with a relative [0,1] brightness value
    based on the "magnitude" column.

    Parameters
    ----------
    object_table : astropy.table.QTable
        Table of objects.

    Returns
    -------
    astropy.table.QTable
        Table with added "brightness" column.
    """
    object_table["flux"] = magnitude_to_flux(object_table["magnitude"])
    object_table["brightness"] = np.log10(
        object_table["flux"]
    )  # since humans see brightness log-scaled

    object_table["brightness"] = linear_rescale(
        object_table["brightness"], new_min=MINIMUM_BRIGHTNESS, new_max=1
    )

    object_table.remove_column("flux")
    return round_columns(object_table, ["brightness"])


def pixel_in_frame(xy: IntArray, image_pixels: int) -> bool:
    """Check if an xy pixel is in a square frame of size `image_pixels`.

    Parameters
    ----------
    xy : IntArray
        Pixel.
    image_pixels : int
        Frame size.

    Returns
    -------
    bool
        Whether the pixel is in the frame.
    """
    x_in = 0 <= xy[0] < image_pixels
    y_in = 0 <= xy[1] < image_pixels

    return x_in and y_in


def add_object_to_frame(
    object_row: Row,
    frame: FloatArray,
    area_mesh: IntArray,
    brightness_scale_mesh: FloatArray,
) -> FloatArray:
    """Add a celestial object to the image.

    Parameters
    ----------
    object_row : astropy.table.Row
        Row of object table.
    frame : FloatArray
        RGB image.
    area_mesh : IntArray
        Mesh describing the area to which light from a single object can spread.
    brightness_scale_mesh : FloatArray
        Mesh describing the dimming of that light.

    Returns
    -------
    FloatArray
        `frame` with the object added in.
    """

    offset_xy = np.array(
        [area_mesh[0] + object_row["x"], area_mesh[1] + object_row["y"]]
    )

    for mesh_xy, _ in np.ndenumerate(area_mesh[0]):
        frame_xy = offset_xy[:, *mesh_xy]  # type: ignore[arg-type]
        if pixel_in_frame(frame_xy, frame.shape[-1]):

            weight = brightness_scale_mesh[*mesh_xy] * object_row["brightness"]
            old_rgb = frame[:, *frame_xy]

            new_rgb = np.average(
                [object_row["rgb"], old_rgb], weights=[weight, 1 - weight], axis=0
            )
            frame[:, *frame_xy] = new_rgb

    return frame


def fill_frame_objects(
    index: int,
    frame: FloatArray,
    objects_table: QTable,
    image_settings: ImageSettings,
    verbose_level: int,
) -> tuple[int, FloatArray]:
    """Pickle-able function to call `add_object_to_frame` for a whole table of objects.

    Parameters
    ----------
    index : int
        The frame number.
    frame : FloatArray
        RGB image.
    objects_table : astropy.table.QTable
        Table of objects to add.
    image_settings : ImageSettings
        Configuration.
    verbose_level : int
        How much detail to print.

    Returns
    -------
    tuple[int, FloatArray]
        Frame number and updated image.
    """
    # calculate the xy coordinates for objects for this wcs
    objects_table["skycoord"] = SkyCoord(
        ra=objects_table["ra"], dec=objects_table["dec"], unit="deg"
    )
    xy = np.flipud(
        np.round(objects_table["skycoord"].to_pixel(image_settings.wcs_objects[index]))
    ).astype(int)
    objects_table["x"] = xy[0]
    objects_table["y"] = xy[1]
    objects_table.remove_column("skycoord")

    for row in objects_table:
        frame = add_object_to_frame(
            row,
            frame,
            image_settings.area_mesh,
            image_settings.brightness_scale_mesh,
        )

    if verbose_level > 1:
        print(f"Added {len(objects_table)} objects to image {index}.")

    return index, frame


def prepare_object_table(
    image_settings: ImageSettings,
    star_table: QTable,
    planet_tables: list[QTable],
    frame: int,
) -> QTable:
    """Converts the star and planet tables into a single combined unit for a
    given frame.

    Parameters
    ----------
    image_settings : ImageSettings
        Configuration.
    star_table : astropy.table.QTable
        Star table.
    planet_tables : list[astropy.table.QTable]
        List of planet tables.
    frame : int
        Frame number to generate for.

    Returns
    -------
    astropy.table.QTable
        Combined table.
    """
    object_table = vstack([star_table, planet_tables[frame]])

    # filter by magnitude
    current_maximum_magnitude = get_timed_magnitude(
        image_settings.magnitude_mapping, image_settings.local_datetimes[frame]
    )
    object_table = filter_objects_brightness(current_maximum_magnitude, object_table)

    # filter by FOV
    object_table["skycoord"] = SkyCoord(ra=object_table["ra"], dec=object_table["dec"])
    object_table = filter_objects_fov(
        image_settings.observation_radec[frame],
        image_settings.field_of_view,
        object_table,
    )

    if len(object_table) == 0:
        return object_table

    # make pickleable
    object_table["ra"] = object_table["ra"].to(u.deg).data
    object_table["dec"] = object_table["dec"].to(u.deg).data

    object_table = get_scaled_brightness(object_table)

    object_table["rgb"] = [
        image_settings.object_colours[stype] for stype in object_table["spectral_type"]
    ]

    object_table.remove_columns(["id", "magnitude", "spectral_type", "skycoord"])

    return object_table
