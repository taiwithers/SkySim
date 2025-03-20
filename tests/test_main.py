"""Tests for the main callable of SkySim."""

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from skysim.__main__ import main
from skysim.settings import PlotSettings


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
    sys.argv.append(str(config_path))
    main()
    sys.argv = sys.argv[:-1]

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
