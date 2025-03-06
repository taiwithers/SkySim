# pylint: disable=all

# skysim. is required to run file as python <file>, but not for poetry install
from skysim.plot import create_plot
from skysim.populate import create_image_matrix
from skysim.query import get_body_locations, get_planet_table, get_star_table
from skysim.settings import load_from_toml


def main() -> None:
    # pylint: disable=missing-function-docstring
    image_settings, plot_settings = load_from_toml(
        "/home/taiwithers/projects/skysim/tests/minimal_multiframe.toml"
    )
    # print(image_settings, plot_settings)

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

    PROFILING = False
    image = create_image_matrix(image_settings, planet_tables, star_table, PROFILING)

    create_plot(plot_settings, image)

    # from matplotlib import pyplot as plt

    # plt.imshow(image[0])
    # plt.savefig("test.png")
