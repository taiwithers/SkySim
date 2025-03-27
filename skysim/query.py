"""Query Simbad & Astropy to get information about celestial objects, using an
`ImageSettings` object to filter the data.
"""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

import warnings
from collections.abc import Collection
from typing import Any

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body
from astropy.table import QTable, Table, unique
from astropy.time import Time
from astroquery.exceptions import NoResultsWarning
from astroquery.simbad import Simbad
from pydantic import PositiveFloat
from pyvo.dal.exceptions import DALQueryError

from skysim.colours import RGBTuple
from skysim.utils import round_columns

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
        "spectral_type",
    ],
    "dtype": [str, float, float, float, str],
    "units": [None, "deg", "deg", None, None],
}
"""Basic table structure used for celestial objects."""


FALLBACK_SPECTRAL_TYPE = "fallback"


# Methods


## Top-Level Query Methods


def get_body_locations(
    observation_times: Time, earth_location: EarthLocation
) -> dict[str, SkyCoord]:
    """Get ephemeris for the sun/earth/planets.

    Parameters
    ----------
    observation_times : Time
        Times to check for.
    earth_location : EarthLocation
        Viewing location.

    Returns
    -------
    dict[str, SkyCoord]
        Locations for sun, earth, planets as dictionary.
    """

    locations = {
        name: get_body(name, observation_times, location=earth_location)
        for name in (list(SOLARSYSTEM_BODIES["name"].data) + ["sun", "earth"])
    }
    return locations


def get_planet_table(
    body_locations: dict[str, SkyCoord],
) -> list[QTable]:
    """
    Get the planetary information at each observing time.

    Parameters
    ----------
    body_locations : dict[str,SkyCoord]
        Dictionary of sun and planet locations for each observation time
        (includes earth).

    Returns
    -------
    list[QTable]
        QTable of planetary info for each observing time.
    """
    sun_locations = body_locations.pop("sun")
    earth_locations = body_locations.pop("earth")
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
    verbose_level: int = 1,
) -> QTable:
    """
    Query Simbad to get celestial objects.

    Parameters
    ----------
    observation_radec : SkyCoord
        RA, Dec coordinates that get observed.
    field_of_view : u.Quantity[angle]
        Diameter of observation.
    maximum_magnitude : float
        Highest magnitude value to search for.
    object_colours : dict[str, RGBTuple]
        Colours of the objects - used to check if spectral types are valid.
    verbose_level : int, optional
        How much detail to print.

    Returns
    -------
    QTable
        Table of all valid celestial objects.
    """
    query_result = run_simbad_query(
        "region",
        extra_columns=["otype", "V", "ids", "sp_type"],
        coordinates=observation_radec,
        radius=field_of_view / 2,
        criteria=f"otype != 'err' AND V < {maximum_magnitude}",
    )
    # remove/rename columns
    query_result = clean_simbad_table_columns(query_result)

    # remove the "ids" column & repurposes the "id" column
    query_result = get_star_name_column(query_result)

    if len(query_result) == 0:
        if verbose_level > 1:
            print("Query to SIMBAD resulted in no objects.")
        return query_result

    # spectral types
    spectral_types = get_spectral_types(object_colours)
    query_result = simplify_spectral_types(query_result, spectral_types)

    # remove child elements
    query_result = remove_child_stars(query_result, maximum_magnitude)

    # final general cleanup
    query_result = round_columns(query_result)
    query_result = unique(query_result)

    if verbose_level > 1:
        print(f"Query to SIMBAD resulted in {len(query_result)} objects.")
    return query_result


## Helper Methods


def get_spectral_types(object_colours: dict[str, RGBTuple]) -> list[str]:
    """Convert the user-input object colours dictionary to a list of valid
    spectral types.

    Parameters
    ----------
    object_colours : dict[str, RGBTuple]
        User input.

    Returns
    -------
    list[str]
        Acceptable spectral types.
    """
    spectral_types = [
        i for i in object_colours.keys() if i not in SOLARSYSTEM_BODIES["name"]
    ]
    return [i for i in spectral_types if i != FALLBACK_SPECTRAL_TYPE]


def run_simbad_query(
    query_type: str, extra_columns: Collection[str] = (), **kwargs: Any
) -> QTable:
    """Query SIMBAD with either a region or TAP request.

    Parameters
    ----------
    query_type : str
        "region" or "tap" - the type of request to send.
    extra_columns : Collection[str], optional
        Extra columns to add to SIMBAD outputs. Only valid for "region" query
        type. Default is ().
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
            Simbad.add_votable_fields(*extra_columns)
            result = QTable(Simbad.query_region(**kwargs))
        elif query_type == "tap":
            if len(extra_columns) > 0:
                raise ValueError(  # TODO: add test for this error
                    f"{extra_columns=} was passed to run_simbad_query, but "
                    f"{query_type=} which doesn't support that."
                )
            result = QTable(Simbad.query_tap(**kwargs))
        else:
            raise ValueError(  # TODO: add test for this error
                f'{query_type=} is invalid, should be one of ["region","tap"].'
            )
    Simbad.reset_votable_fields()
    return result


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


def get_child_stars(
    parent_stars: tuple[str], maximum_magnitude: float
) -> Collection[str]:
    """Query SIMBAD for any child objects of `parent_stars`.

    Parameters
    ----------
    parent_stars : tuple[str]
        SIMAD ids.
    maximum_magnitude : float
        Filtering value for the children.

    Returns
    -------
    Collection[str]
        Child ids.
    """

    parent_stars_list = []
    for star in parent_stars:
        if "/" in star:
            star = star[: star.index("/")]
        if "'" in star:
            star = star.replace("'", "''")
        parent_stars_list.append(star)

    # str(tuple-with-one-element) adds a trailing comma, which trips up SIMBAD,
    # so we do the string conversion ourself in this case
    if len(parent_stars_list) == 1:
        parent_stars_string = f"('{parent_stars_list[0]}')"
    else:
        parent_stars_string = f"{tuple(str(i) for i in parent_stars_list)}"

    # write the query
    parent_query_adql = f"""
        SELECT main_id as "child", allfluxes.V
        FROM h_link
        JOIN ident as p on p.oidref=parent
        JOIN basic on oid="child"
        JOIN allfluxes on oid = allfluxes.oidref
        WHERE p.id in {parent_stars_string}
        AND V <= {maximum_magnitude};
    """

    try:
        children = run_simbad_query("tap", query=parent_query_adql)
    except DALQueryError as e:
        # Sometimes one of the parent ids is...problematic
        # if that's the case, just boot it out
        if "1 unresolved identifiers" in e.reason:
            bad_region = e.reason[e.reason.index("[") + 1 : e.reason.index("]")]
            lineno = int(bad_region[2 : bad_region.index(" ")])
            get_col = lambda colstring: int(colstring[colstring.index(" ") + 3 :])
            col_start, col_end = [get_col(a) for a in bad_region.split(" - ")]

            query_split = parent_query_adql.splitlines()
            query_split[lineno - 1] = (
                query_split[lineno - 1][: col_start - 1]
                + query_split[lineno - 1][col_end + 1 :]
            )

            parent_query_adql = "\n".join(query_split)
            children = run_simbad_query("tap", query=parent_query_adql)
        else:
            children = QTable(**BASIC_TABLE)
            raise e
    return children["child"].data


def remove_child_stars(star_table: QTable, maximum_magnitude: float) -> QTable:
    """Check the given table for parent-child pairs, and remove the children if
    they exist.

    Parameters
    ----------
    star_table : QTable
        Table to checked.
    maximum_magnitude : float
        Filtering value for the children.

    Returns
    -------
    QTable
        Table with only parent items.
    """
    parents = star_table["id"]  # check all items, regardless of type

    blocksize = 1000
    all_children = []
    n_blocks = int(len(parents) / blocksize)
    for i in range(n_blocks):
        all_children.append(
            get_child_stars(
                tuple(parents.data[i * blocksize : (i + 1) * blocksize]),
                maximum_magnitude,
            )
        )
    all_children.append(
        get_child_stars(tuple(parents.data[n_blocks * blocksize :]), maximum_magnitude)
    )
    child_items = np.concatenate(all_children)  # type: ignore[arg-type,var-annotated]

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
    for i in range(len(spectral_type), 0, -1):
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
        "otype",
    ]
    for colname in columns_to_remove:
        if colname in table.colnames:
            table.remove_column(colname)

    renames = {
        "main_id": "id",
        "V": "magnitude",
        "sp_type": "spectral_type",
    }

    for old, new in renames.items():
        if old in table.colnames:
            table.rename_column(old, new)

    return table
