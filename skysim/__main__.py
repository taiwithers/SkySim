"""Calling module for the SkySim package."""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

import sys

# skysim. is required to run file as python <file>, but not for poetry install
from skysim.plot import create_plot
from skysim.populate import create_image_matrix
from skysim.query import get_body_locations, get_planet_table, get_star_table
from skysim.settings import confirm_config_file, load_from_toml


def main() -> None:
    """Entrypoint for the SkySim package. Calls the high-level functions from
    the other modules.
    """
    config_path = confirm_config_file(sys.argv)
    image_settings, plot_settings = load_from_toml(config_path)

    star_table = get_star_table(
        image_settings.observation_radec,
        image_settings.field_of_view,
        image_settings.maximum_magnitude,
        image_settings.object_colours,
    )

    body_locations = get_body_locations(
        image_settings.observation_times, image_settings.earth_location
    )
    planet_tables = get_planet_table(body_locations)

    image = create_image_matrix(image_settings, planet_tables, star_table)  # type: ignore[arg-type]

    create_plot(plot_settings, image)  # type: ignore[arg-type]
