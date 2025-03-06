"""
Test the skysim query module.
"""

import pytest
from astropy.table import QTable

from skysim.query import remove_child_stars  # pylint: disable=unused-import
from skysim.query import (
    FALLBACK_SPECTRAL_TYPE,
    SOLARSYSTEM_BODIES,
    get_body_locations,
    get_child_stars,
    get_planet_magnitude,
    get_planet_table,
    get_single_spectral_type,
    get_spectral_types,
    get_star_table,
    run_simbad_query,
)
from skysim.settings import (  # pylint: disable=unused-import
    ImageSettings,
    Settings,
)

# need to import minimal_config_path for settings/image_settings to work?
from .test_settings import (  # pylint: disable=unused-import
    config_path,
    image_settings,
    settings,
)


@pytest.fixture
def planet_table(settings: Settings) -> list[QTable]:
    # pylint: disable=missing-function-docstring
    body_locations = get_body_locations(
        settings.observation_times, settings.earth_location
    )
    return get_planet_table(body_locations)


@pytest.fixture
def star_table(image_settings: ImageSettings) -> QTable:
    # pylint: disable=missing-function-docstring
    return get_star_table(
        image_settings.observation_radec,
        image_settings.field_of_view,
        image_settings.maximum_magnitude,
        image_settings.object_colours,
    )


def test_planet_table(settings: Settings, planet_table: list[QTable]) -> None:
    """
    Tests for the planet queries.

    Parameters
    ----------
    settings : Settings
        `Settings` object to compare against.
    planet_table : list[QTable]
        List of tables containing planetary information.
    """
    # check that the correct number of calls were made to get_body
    assert len(planet_table) == settings.frames

    # check that each table has entries for each planet
    assert all(
        len(planet_table[i]) == len(SOLARSYSTEM_BODIES["name"])
        for i in range(settings.frames)
    )


def test_star_table(star_table: QTable) -> None:
    """
    Tests for the star table query.

    Parameters
    ----------
    star_table : QTable
        Table of results from SIMBAD.
    """
    # for this particular test case we should have results
    assert len(star_table) > 0


def test_simbad_query() -> None:
    """Test the SIMBAD querying function."""
    with pytest.raises(ValueError):
        run_simbad_query("fake_query_type")

    children = get_child_stars(tuple(["NGC 1981"]))
    assert len(children) > 0  # confirm that the parent query is working


def test_planet_magnitude() -> None:
    """Test the magnitude calculation."""
    base_magnitude = 19
    earth_distance = 1
    sun_distance = 1

    # if earth and sun distance multiple to 1, the result should equal base_magnitude
    assert (
        get_planet_magnitude(base_magnitude, sun_distance, earth_distance)
        == base_magnitude
    )

    base_magnitude = 1
    earth_distance = 2
    sun_distance = 50
    # if earth and sun distance multiple to 100, result should be 10 *
    # base_magnitude
    assert (
        get_planet_magnitude(base_magnitude, sun_distance, earth_distance)
        == 10 + base_magnitude
    )

    # order of earth and sun distance shouldn't matter
    assert get_planet_magnitude(
        base_magnitude, earth_distance, sun_distance
    ) == get_planet_magnitude(base_magnitude, sun_distance, earth_distance)


def test_remove_children() -> None:
    """Not implemented."""
    return


def test_clean_spectral_type(image_settings: ImageSettings) -> None:
    """Confirm that cleaning the SIMBAD spectral types works as expected.

    Parameters
    ----------
    image_settings : ImageSettings
        From `image_settings()` fixture.
    """
    test_cases = {
        "": FALLBACK_SPECTRAL_TYPE,
        "?": FALLBACK_SPECTRAL_TYPE,
        "K": "K",
        "KII": "K",
    }
    spectral_types = get_spectral_types(image_settings.object_colours)
    for original, check in test_cases.items():
        assert get_single_spectral_type(original, spectral_types) == check
