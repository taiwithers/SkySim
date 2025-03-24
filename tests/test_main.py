"""Tests for the main callable of SkySim."""

from pathlib import Path
from typing import Optional

import numpy as np
import pytest
from PIL import Image

from skysim.__main__ import main
from skysim.settings import PlotSettings

from .utils import TEST_ROOT_PATH


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
