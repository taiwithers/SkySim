# pylint: disable=all
# mypy: ignore-errors

import sys
from pathlib import Path

import numpy as np

# skysim. is required to run file as python <file>, but not for poetry install
from skysim.plot import create_plot
from skysim.populate import create_image_matrix, get_empty_image
from skysim.query import get_body_locations, get_planet_table, get_star_table
from skysim.settings import confirm_config_file, load_from_toml

FAST = True
PROFILING = False


def main() -> None:
    # pylint: disable=missing-function-docstring
    config_path = confirm_config_file(sys.argv)
    image_settings, plot_settings = load_from_toml(config_path)

    if FAST:
        image = get_empty_image(image_settings.frames, image_settings.image_pixels)
        image = np.moveaxis(image, 1, -1)
    else:
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

        image = create_image_matrix(
            image_settings, planet_tables, star_table, PROFILING
        )

    create_plot(plot_settings, image)
    # from matplotlib import pyplot as plt

    # plt.imshow(image[0])
    # plt.savefig("test.png")
