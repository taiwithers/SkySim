"""Test the plotting functions of SkySim."""

from pathlib import Path

import pytest

from skysim.plot import construct_ffmpeg_call, movie_cleanup, run_ffmpeg
from skysim.settings import PlotSettings, Settings, toml_to_dicts


def test_construct_ffmpeg_call(plot_settings: PlotSettings) -> None:
    """Test that the ffmpeg call is being generated correctly.

    Parameters
    ----------
    plot_settings : PlotSettings
        Pytest fixture.
    """
    command = construct_ffmpeg_call(plot_settings)
    filename_string = str(plot_settings.filename)
    assert Path(command[-len(filename_string) :]) == plot_settings.filename


@pytest.mark.xfail
def test_run_ffmpeg(tmp_path: Path, config_path: Path) -> None:
    """Test that the ffmpeg call fails if called at an inappropriate time.

    Parameters
    ----------
    tmp_path : Path
        Pytest fixture.

    config_path : Path
        Pytest fixture.
    """
    settings_config, _, plot_config = toml_to_dicts(config_path)
    plot_config["tempfile_path"] = tmp_path

    settings = Settings(**settings_config)
    plot_settings = settings.get_plot_settings(**plot_config)

    run_ffmpeg(plot_settings)  # run ffmpeg, which should fail since there are no images


@pytest.mark.xfail(raises=ValueError)
def test_movie_cleanup() -> None:
    """Test that the `movie_cleanup` function doesn't remove things it's not
    supposed to.
    """
    filenames = [Path("tests/test_plot.py")]
    directory = Path("skysim")

    try:
        verbose = 0
        movie_cleanup(filenames, directory, verbose)
        # this should raise an error since the directory won't be deleted

    except ValueError as e:

        # the files should not have been deleted
        for filename in filenames:
            assert filename.exists()

        raise e
