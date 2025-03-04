"""
Query Simbad & Astropy to get information about celestial objects.
"""

import warnings
from collections.abc import Collection, Mapping

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body
from astropy.table import QTable, Table, unique
from astropy.time import Time
from astroquery.exceptions import NoResultsWarning
from astroquery.simbad import Simbad
from pydantic import PositiveFloat

from .colours import RGBTuple

# Constants


SOLARSYSTEM_BODIES = Table(
    {
        "name": [
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        ],
        "magnitude.offset": [
            -0.613,
            -4.384,
            -1.601,
            -9.395,
            -8.914,
            -7.11,
            -7,
        ],
    }
)
"""Dictionary of bodies (planets) and base magnitudes (used in
`get_planet_magnitude`)
"""

BASIC_TABLE = {
    "names": [
        "id",
        "ra",
        "dec",
        "magnitude",
        "object_type",
        "spectral_type",
    ],
    "dtype": [object, float, float, float, object, str],
    "units": [None, "deg", "deg", None, None, None],
}
"""Basic table structure used for celestial objects."""


FALLBACK_SPECTRAL_TYPE = "fallback"


# Methods


## Primary Query Methods


def get_planet_table(
    earth_location: EarthLocation, observation_times: Time
) -> list[QTable]:
    """
    Get the planetary information at each observing time.

    Parameters
    ----------
    earth_location : EarthLocation
        Location of observation.
    observation_times : Time
        Time(s) of observation.

    Returns
    -------
    list[QTable]
        QTable of planetary info for each observing time.
    """

    sun_locations = get_body("sun", observation_times, location=earth_location)
    earth_locations = get_body("earth", observation_times, location=earth_location)

    body_locations = {
        name: get_body(name, observation_times, location=earth_location)
        for name in SOLARSYSTEM_BODIES["name"]
    }

    planet_table = []

    for i, (sun, earth) in enumerate(zip(sun_locations, earth_locations)):
        this_time = QTable(**BASIC_TABLE)

        for name, mag_offset in SOLARSYSTEM_BODIES[["name", "magnitude.offset"]]:
            body_location = body_locations[name][i]
            sun_distance = body_location.separation_3d(sun).to(u.au).value
            earth_distance = body_location.separation_3d(earth).to(u.au).value
            row = {
                "ra": body_location.ra,
                "dec": body_location.dec,
                "magnitude": get_planet_magnitude(
                    mag_offset, sun_distance, earth_distance
                ),
                "spectral_type": name,
                "id": name,
            }
            this_time.add_row(row)

        this_time = round_columns(this_time)
        planet_table.append(this_time)

    return planet_table


def get_star_table(
    observation_radec: SkyCoord,
    field_of_view: u.Quantity["angle"],  # type: ignore[type-arg, name-defined]
    maximum_magnitude: float,
    object_colours: dict[str, RGBTuple],
) -> QTable:
    """
    Query Simbad to get celestial objects.

    Parameters
    ----------
    observation_radec : SkyCoord
        RA, Dec coordinates that get observed.
    field_of_view : u.Quantity["angle"]
        Diameter of observation.
    maximum_magnitude : float
        Highest magnitude value to search for.
    object_colours : dict[str, RGBTuple]
        Colours of the objects - used to check if spectral types are valid.

    Returns
    -------
    QTable
        Table of all valid celestial objects.
    """
    Simbad.reset_votable_fields()
    Simbad.add_votable_fields("otype", "V", "ids", "sp_type")
    query_result = run_simbad_query(
        "region",
        coordinates=observation_radec,
        radius=field_of_view / 2,
        criteria=f"otype != 'err' AND V < {maximum_magnitude}",
    )
    if len(query_result) == 0:
        return query_result

    # remove/rename columns
    query_result = clean_simbad_table_columns(query_result)

    # spectral types
    spectral_types = [
        i for i in object_colours.keys() if i not in SOLARSYSTEM_BODIES["name"]
    ]
    spectral_types = [i for i in spectral_types if i != FALLBACK_SPECTRAL_TYPE]
    query_result = simplify_spectral_types(query_result, spectral_types)

    # remove child elements
    query_result = remove_child_stars(query_result)

    # remove the "ids" column & repurposes the "id" column
    query_result = get_star_name_column(query_result)

    # final general cleanup
    query_result = round_columns(query_result)
    query_result = unique(query_result)

    return query_result


## Helper Methods


def run_simbad_query(query_type: str, **kwargs: Mapping) -> QTable:
    """Query SIMBAD with either a region or TAP request.

    Parameters
    ----------
    query_type : str
        "region" or "tap" - the type of request to send.
    **kwargs : Mapping
        Unpacked and passed to the query function.

    Returns
    -------
    QTable
        Simbad result.

    Raises
    ------
    ValueError
        Raised if `query_type` is not "region" or "tap".
    """
    result = QTable(**BASIC_TABLE)
    with warnings.catch_warnings(action="ignore", category=NoResultsWarning):
        if query_type == "region":
            result = QTable(Simbad.query_region(**kwargs))
        elif query_type == "tap":
            result = QTable(Simbad.query_tap(**kwargs))
        else:
            raise ValueError(
                f'{query_type=} is invalid, should be one of ["region","tap"].'
            )
    return result


def round_columns(
    table: QTable,
    column_names: Collection[str] = ("ra", "dec", "magnitude"),
    decimals: int | Collection[int] = 5,
) -> QTable:
    """
    Round columns of an Astropy Table.

    Parameters
    ----------
    table : Table
        Table.
    column_names : list[str], optional
        Names of columns to be rounded, by default ["ra","dec","magnitude"].
    decimals : int|list[int], optional
        Number of decimal places to keep, can be list of ints (same size as
        `column_names`) or a single value, by default 5.

    Returns
    -------
    Table
        `table` with `column_names` rounded to `decimals`.
    """

    if isinstance(decimals, int):
        decimals = [decimals] * len(column_names)
    else:
        if len(decimals) != len(column_names):
            raise ValueError
    for name, roundto in zip(column_names, decimals):
        table[name] = table[name].round(roundto)

    return table


def get_planet_magnitude(
    base_magnitude: float,
    distance_to_sun: PositiveFloat,
    distance_to_earth: PositiveFloat,
) -> float:
    """Calculate the magnitude for a planet.

    Parameters
    ----------
    base_magnitude : float
        Static base magnitude for the planet.
    distance_to_sun : PositiveFloat
        Distance (in au) from the planet to the sun.
    distance_to_earth : PositiveFloat
        Distance (in au) from the planet to the Earth.

    Returns
    -------
    float
        The magnitude.
    """
    return (
        5 * np.log10(distance_to_sun * distance_to_earth).astype(float) + base_magnitude
    )


def get_star_name_column(star_table: QTable) -> QTable:
    """Create human-readable `name` column.

    Parameters
    ----------
    star_table : QTable
        Table of stars from which to generate the name column from the `ids`
        column.

    Returns
    -------
    QTable
        `star_table` with the `id` column replaced by a human-readable `name`
        column, and the `ids` column removed.
    """

    star_table["ids_list"] = [i.split("|") for i in star_table["ids"]]
    names_column = []
    for simbad_id, namelist in zip(star_table["id"].data, star_table["ids_list"].data):
        item_names = [n[5:] for n in namelist if "NAME" in n]
        if len(item_names) == 0:
            names_column.append(simbad_id)
        elif len(item_names) == 1:
            names_column.append(item_names[0])
        else:
            names_column.append("/".join(item_names))
    star_table.replace_column("id", names_column)
    star_table.remove_columns(["ids", "ids_list"])

    return star_table


def remove_child_stars(star_table: QTable) -> QTable:
    """Check the given table for parent-child pairs, and remove the children if
    they exist.

    Parameters
    ----------
    star_table : QTable
        Table to checked.

    Returns
    -------
    QTable
        Table with only parent items.
    """
    parents = star_table["id"]  # check all items, regardless of type
    parents_string = tuple(parents.data)
    parent_query_adql = f"""
            SELECT main_id AS "child_id",
            parent_table.id AS "parent_id"
            FROM (SELECT oidref, id FROM ident WHERE id IN {parents_string}) AS parent_table,
            basic JOIN h_link ON basic.oid = h_link.child
            WHERE h_link.parent = parent_table.oidref;
        """
    child_items = run_simbad_query("tap", query=parent_query_adql)["child_id"].data

    star_table.add_index("id")
    for child_id in child_items:
        if child_id in star_table["id"]:
            star_table.remove_rows(star_table.loc_indices[child_id])
    star_table.remove_indices("id")
    return star_table


def get_single_spectral_type(
    spectral_type: str,
    acceptable_types: Collection[str],
) -> str:
    """Process a SIMBAD spectral type into one of `acceptable_types` or
    `FALLBACK_SPECTRAL_TYPE`.

    Parameters
    ----------
    spectral_type : str
        The spectral type as given by SIMBAD.
    acceptable_types : Collection[str]
        Collection of acceptable spectral types.

    Returns
    -------
    str
        The best match to `acceptable_types` or `FALLBACK_SPECTRAL_TYPE`.
    """
    if len(spectral_type) == 0:
        return FALLBACK_SPECTRAL_TYPE

    # start with most specific type, and work backwards
    for i in range(len(spectral_type), 1, -1):
        if spectral_type[:i] in acceptable_types:
            return spectral_type[:i]

    return FALLBACK_SPECTRAL_TYPE


def simplify_spectral_types(
    star_table: QTable,
    acceptable_types: Collection[str],
) -> QTable:
    """Replaces the `spectral_type` column of a table with simplified versions
    via `get_single_spectral_type`.

    Parameters
    ----------
    star_table : QTable
        Table with a `spectral_type` column.
    acceptable_types : Collection[str]
        Collection of acceptable spectral types.

    Returns
    -------
    QTable
        `star_table` with a replaced `spectral_type` column.
    """
    old_spectral_types = star_table["spectral_type"].data
    star_table["spectral_type"] = [
        get_single_spectral_type(st, acceptable_types) for st in old_spectral_types
    ]
    return star_table


def clean_simbad_table_columns(table: QTable) -> QTable:
    """Remove and rename some SIMBAD columns - does not fail if the columns do
    not exist.

    Parameters
    ----------
    table : QTable
        Table to operate on.

    Returns
    -------
    QTable
        "Cleaned" table.
    """
    columns_to_remove = [
        "coo_err_min",
        "coo_err_angle",
        "coo_wavelength",
        "coo_bibcode",
        "coo_err_maj",
    ]
    for colname in columns_to_remove:
        if colname in table.colnames:
            table.remove_column(colname)

    renames = {
        "main_id": "id",
        "otype": "object_type",
        "V": "magnitude",
        "sp_type": "spectral_type",
    }

    for old, new in renames.items():
        if old in table.colnames:
            table.rename_column(old, new)

    return table
