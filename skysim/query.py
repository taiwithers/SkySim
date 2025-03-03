"""
Query Simbad & Astropy to get information about celestial objects.
"""

import warnings
from collections.abc import Collection

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body
from astropy.table import QTable, Table, unique
from astropy.time import Time
from astroquery.exceptions import NoResultsWarning
from astroquery.simbad import Simbad

from skysim.colours import RGBTuple


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
    solarsys_bodies = Table(
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

    sun_locations = get_body("sun", observation_times, location=earth_location)
    earth_locations = get_body("earth", observation_times, location=earth_location)

    body_locations = {
        name: get_body(name, observation_times, location=earth_location)
        for name in solarsys_bodies["name"]
    }

    planet_table = []

    for i, (sun, earth) in enumerate(zip(sun_locations, earth_locations)):
        this_time = QTable(
            names=[
                "id",
                "ra",
                "dec",
                "magnitude",
                "object_type",
                "spectral_type",
                "name",
            ],
            dtype=[object, float, float, float, object, str, str],
            units=[None, "deg", "deg", None, None, None, None],
        )

        for name, mag_offset in solarsys_bodies[["name", "magnitude.offset"]]:
            body_location = body_locations[name][i]
            sun_distance = body_location.separation_3d(sun).to(u.au).value
            earth_distance = body_location.separation_3d(earth).to(u.au).value
            row = {
                "ra": body_location.ra,
                "dec": body_location.dec,
                "magnitude": round(
                    5 * np.log10(sun_distance * earth_distance) + mag_offset, 3
                ),
                "spectral_type": name,
                "name": name,
                "id": name,
            }
            this_time.add_row(row)

        this_time = round_columns(this_time)
        planet_table.append(this_time)

    return planet_table


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
    with warnings.catch_warnings(action="ignore", category=NoResultsWarning):
        query_result = QTable(
            Simbad.query_region(
                observation_radec,
                radius=field_of_view / 2,
                criteria=f"otype != 'err' AND V < {maximum_magnitude}",
            )
        )

    if len(query_result) == 0:
        return QTable(
            {
                k: []
                for k in [
                    "id",
                    "ra",
                    "dec",
                    "magnitude",
                    "spectral_type",
                    "object_type",
                    "name",
                ]
            },
            dtype=[object, float, float, float, object, object, str],
            units=[None, "deg", "deg", None, None, None, None],
        )

    # clean up the result
    columns_to_remove = [
        "coo_err_min",
        "coo_err_angle",
        "coo_wavelength",
        "coo_bibcode",
        "coo_err_maj",
    ]
    for colname in columns_to_remove:
        query_result.remove_column(colname)

    # rename columns
    query_result.rename_column("main_id", "id")
    query_result.rename_column("otype", "object_type")
    query_result.rename_column("V", "magnitude")
    query_result.rename_column("sp_type", "spectral_type")

    query_result = round_columns(query_result)

    spectral_types = []
    for i in query_result["spectral_type"].data:
        if (len(i) > 0) and (i[0] in object_colours.keys()):
            spectral_types.append(i[0])
        else:
            spectral_types.append("")
    query_result["spectral_type"] = spectral_types

    # create human-readable name column
    query_result["ids_list"] = [i.split("|") for i in query_result["ids"]]
    names_column = []
    for simbad_id, namelist in zip(
        query_result["id"].data, query_result["ids_list"].data
    ):
        item_names = [n[5:] for n in namelist if "NAME" in n]
        if len(item_names) == 0:
            names_column.append(simbad_id)
        elif len(item_names) == 1:
            names_column.append(item_names[0])
        else:
            names_column.append("/".join(item_names))
    query_result["name"] = names_column
    query_result.remove_columns(["ids", "ids_list"])

    # remove child elements
    parents = query_result["id"]  # check all items, regardless of type
    parents_string = tuple(parents.data)

    # TODO: separate here & add tests for parent querying
    parent_query_adql = f"""
        SELECT main_id AS "child_id",
        parent_table.id AS "parent_id"
        FROM (SELECT oidref, id FROM ident WHERE id IN {parents_string}) AS parent_table,
        basic JOIN h_link ON basic.oid = h_link.child
        WHERE h_link.parent = parent_table.oidref;
    """
    with warnings.catch_warnings(action="ignore", category=NoResultsWarning):
        hierarchies = Simbad.query_tap(parent_query_adql)
    children = unique(hierarchies)["child_id"].data
    query_result.add_index("id")
    for child_id in children:
        if child_id in query_result["id"]:
            query_result.remove_rows(query_result.loc_indices[child_id])

    query_result = unique(query_result)

    return query_result
