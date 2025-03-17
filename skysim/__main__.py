# pylint: disable=all
# mypy: ignore-errors

import sys
from pathlib import Path

import numpy as np

# skysim. is required to run file as python <file>, but not for poetry install
from skysim.plot import create_plot
from skysim.populate import create_image_matrix, get_empty_image
from skysim.query import get_body_locations, get_planet_table, get_star_table
from skysim.settings import load_from_toml


# todo: move this into settings.py
def confirm_config_file():
    # pylint: disable=missing-function-docstring
    cwd = Path(".")  # path of calling shell, not current file
    if len(sys.argv) == 1:
        raise ValueError("No config file given.")
    input_config_path = sys.argv[-1]
    config_path = Path(input_config_path).resolve()

    if not config_path.exists():
        raise ValueError(f"{config_path} does not exist.")
    if not config_path.is_file():
        raise ValueError(f"{config_path} is not a file.")
    if config_path.suffix != ".toml":
        raise ValueError(f"{config_path} does not have a '.toml' extension.")

    return config_path


FAST = True
PROFILING = False


def main() -> None:
    # pylint: disable=missing-function-docstring
    config_path = confirm_config_file()
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
