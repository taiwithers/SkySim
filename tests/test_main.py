"""Tests for the main callable of SkySim."""

from pathlib import Path
from typing import Optional

import numpy as np
import pytest
from PIL import Image

from skysim.__main__ import main
from skysim.settings import PlotSettings

from .utils import TEST_ROOT_PATH


@pytest.mark.flaky(reruns=2, reruns_delay=5, only_rerun="ConnectionError")
@pytest.fixture(scope="session")
def created_imagepath(config_path: Path, plot_settings: PlotSettings) -> Path:
    """Run the main SkySim command, return the saved filename, and clean up once
    the requesting function is finished.

    Parameters
    ----------
    config_path : Path
        Pytest fixture.
    plot_settings : PlotSettings
        Pytest fixture.

    Yields
    ------
    Path
        The file output by main().
    """
    main([str(config_path)])

    yield plot_settings.filename

    plot_settings.filename.unlink()


def test_image_creation(created_imagepath: Path) -> None:
    """Check that the file was actually created.

    Parameters
    ----------
    created_imagepath : Path
        Filename.
    """
    assert created_imagepath.exists()


def test_image_contents(created_imagepath: Path) -> None:
    """Check that the image contains at least 3 distinct colours. Only runs on
    images, not videos.

    Parameters
    ----------
    created_imagepath : Path
        Filename.
    """
    if created_imagepath.suffix == ".mp4":
        pytest.skip(reason="Can't run PIL-based checks on video files.")
    im = Image.open(created_imagepath)
    rgb = np.array([list(im.getdata(i)) for i in (0, 1, 2)])
    rgb = np.unique(rgb, axis=1)
    n_colours = rgb.shape[1]
    assert n_colours > 2


@pytest.mark.parametrize(
    "args,exception_string",
    [
        ([], "error: the following arguments are required"),
        (["-h"], None),
        (["--help"], None),
        (["a", "b"], "error: unrecognized arguments"),
        ([f"{TEST_ROOT_PATH}/configs/missing_required.toml"], "Required element"),
        ([f"{TEST_ROOT_PATH}/__init__.py"], ".toml"),
    ],
)
def test_main_args(
    capsys: pytest.CaptureFixture[str], args: list[str], exception_string: Optional[str]
) -> None:
    """Test that the correct exceptions are raised when skysim.__main__.main is
    called with incorrect arguments.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Pytest fixture to grab stderr and stdout.
    args : list[str]
        Arguments to pass to `main` for argparse.
    exception_string : Optional[str]
        String that should appear in the exception message, if any.
    """
    with pytest.raises(SystemExit):
        main(args)
    if exception_string is not None:
        exception_message = capsys.readouterr().err
        assert exception_string in exception_message


def test_main_debug() -> None:
    """Check that the debug flag raises ValueErrors instead of SystemExits, and
    that the ValueError has an argument.
    """
    with pytest.raises(SystemExit) as regular_exception:
        main(["bad_config_path"])
    regular_exception_args = regular_exception.value.args[0]
    assert regular_exception_args == 1  # the system exit code

    with pytest.raises(ValueError) as debug_exception:
        main(["--debug", "bad_config_path"])
    debug_exception_args = debug_exception.value.args[
        0
    ]  # should be the string passed to ValueError

    assert len(debug_exception_args) > 1  # string should not be empty


@pytest.mark.flaky(reruns=2, reruns_delay=5, only_rerun="ConnectionError")
@pytest.mark.parametrize(
    "filename,error_message",
    [
        # fail in confirm_config_file
        ("nonexistent.toml", "does not exist."),
        ("not_toml.txt", "does not have"),
        ("", "not a file."),  # points to the configs directory
        # generic key requirements (fail in load_from_toml > toml_to_dicts >
        # check_mandatory_toml_keys)
        ("missing_required.toml", "Required element"),
        ("missing_one_or_more.toml", "One or more of"),
        ("mismatched_all_or_none.toml", "Some but not all of"),
        # toml parsing (fail in load_from_toml > toml_to_dicts)
        ("tomllib_error.toml", "Error reading config file"),
        ("string_angle.toml", "Could not convert angular value"),  # parse_angle_dicts
        # validation of specific values (fail inside the pydantic model)
        ("zero_fps_movie.toml", "Non-zero duration"),
        ("interval_duration_mismatch.toml", "Frequency of snapshots"),
        ("bad_type_date.toml", "Input should be a valid"),
        ("bad_type_date.toml", "Input should be a valid"),
        ("no_image_folder.toml", "parent directory"),
        # fail in plot.py - these sometimes throw connection timed out on the
        # EarthLocation lookup, hence the flaky decorator
        ("no_permissions_image.toml", "Choose a different path"),
        ("no_permissions_tempdir.toml", "Choose a different path"),
    ],
)
def test_bad_configs(filename: str, error_message: str) -> None:
    """Test that the confirm_config_file and load_toml functions throw
    appropriate errors when a bad file is passed in.

    Parameters
    ----------
    filename : str
        Name of the toml file to use for testing (without extension).
    error_message : str
        The error message to check for.
    """
    with pytest.raises(ValueError, match=error_message):
        # without --debug, the result is a SystemExit which doesn't have an
        # error message
        main(["--debug", f"{TEST_ROOT_PATH}/configs/{filename}"])
