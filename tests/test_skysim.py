from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import matplotlib.colors as mpl_colors
import pytest
from astropy import units as u

from skysim.outline import ImageSettings, PlotSettings, Settings

# from ipdb import set_trace as breakpoint  # overriding builtin breakpoint()


@pytest.fixture()
def settings() -> Settings:
    input_location = "Toronto"
    field_of_view = 2 * u.deg
    altitude_angle = 40 * u.deg
    azimuth_angle = 140 * u.deg
    image_pixels = 250

    start_date = date(year=2025, month=2, day=25)
    start_time = time(hour=20, minute=30)
    snapshot_frequency = timedelta(minutes=1)
    duration = timedelta(minutes=2)

    return Settings(
        input_location,
        field_of_view,
        altitude_angle,
        azimuth_angle,
        image_pixels,
        start_date,
        start_time,
        snapshot_frequency,
        duration,
    )


@pytest.fixture()
def image_settings(settings: Settings) -> ImageSettings:
    object_colours = {
        key: mpl_colors.to_rgb(value)
        for key, value in {
            "O": "lightskyblue",
            "B": "lightcyan",
            "A": "white",
            "F": "lemonchiffon",
            "G": "yellow",
            "K": "orange",
            "M": "lightpink",  # "#f9706b",
            "": "white",
            "moon": "white",
            "mercury": "white",
            "venus": "lemonchiffon",
            "mars": "orange",
            "jupiter": "white",
            "saturn": "white",
            "uranus": "white",
            "neptune": "white",
        }.items()
    }
    colour_values = ["#000", "#171726", "dodgerblue", "#00BFFF", "lightskyblue"]
    magnitude_values = [6, 4, 2, 0, -1]

    colour_time_indices = {0: 0, 3: 1, 5: 2, 7: 3, 12: 4, 15: 3, 18: 2, 21: 1, 24: 0}
    magnitude_time_indices = colour_time_indices.copy()

    return settings.get_image_settings(
        object_colours,
        colour_values,
        colour_time_indices,
        magnitude_values,
        magnitude_time_indices,
    )


@pytest.fixture()
def plot_settings(settings: Settings) -> PlotSettings:
    fps = 2
    filename = "SkySim.gif"
    figure_size = (5, 5.5)
    dpi = 250
    return settings.get_plot_settings(fps, filename, figure_size, dpi)


def test_settings(settings: Settings) -> None:
    assert settings.frames == 2
    assert settings.degrees_per_pixel == 0.008 * u.deg
    assert settings.timezone == ZoneInfo("America/Toronto")
    assert not hasattr(settings, "image_settings")
    assert not hasattr(settings, "plot_settings")


def test_image_settings(image_settings: ImageSettings) -> None:
    # copied from test_settings
    assert image_settings.frames == 2
    assert image_settings.degrees_per_pixel == 0.008 * u.deg
    assert image_settings.timezone == ZoneInfo("America/Toronto")

    assert mpl_colors.same_color(image_settings.colour_mapping(0), "black")


def test_plot_settings(plot_settings: PlotSettings) -> None:
    # copied from test_settings
    assert plot_settings.frames == 2
    assert plot_settings.degrees_per_pixel == 0.008 * u.deg
    assert plot_settings.timezone == ZoneInfo("America/Toronto")

    assert isinstance(plot_settings.obs_info, str)
