"""
Test the skysim query module.
"""

import pytest
from astropy.table import QTable

from skysim.query import get_planet_table, get_star_table
from skysim.settings import (  # pylint: disable=unused-import
    ImageSettings,
    PlotSettings,
    Settings,
    SettingsPair,
)

from .test_settings import (  # pylint: disable=unused-import
    manual_image_settings,
    manual_settings,
    minimal_settings,
)


@pytest.fixture
def planet_table(manual_settings: Settings) -> list[QTable]:
    # pylint: disable=missing-function-docstring
    return get_planet_table(
        manual_settings.earth_location, manual_settings.observation_times
    )


@pytest.fixture
def star_table(manual_image_settings: ImageSettings) -> QTable:
    # pylint: disable=missing-function-docstring
    return get_star_table(
        manual_image_settings.observation_radec,
        manual_image_settings.field_of_view,
        manual_image_settings.maximum_magnitude,
        manual_image_settings.object_colours,
    )


def test_planet_table(manual_settings: Settings, planet_table: list[QTable]) -> None:
    """
    Tests for the planet queries.

    Parameters
    ----------
    manual_settings : Settings
        `Settings` object to compare against.
    planet_table : list[QTable]
        List of tables containing planetary information.
    """
    # check that the correct number of calls were made to get_body
    assert len(planet_table) == manual_settings.frames

    # check that each table has entries for each planet
    assert all(len(planet_table[i]) == 7 for i in range(manual_settings.frames))


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
