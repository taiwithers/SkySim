"""
Test the skysim populate module.
"""

import numpy as np
import pytest
from astropy.table import QTable

from skysim.populate import (
    MINIMUM_BRIGHTNESS,
    add_object_to_frame,
    fill_frame_background,
    get_empty_image,
    get_scaled_brightness,
)
from skysim.settings import (
    ImageSettings,
)
from skysim.utils import FloatArray

# need to import minimal_config_path for settings/image_settings to work?
from .test_settings import config_path, image_settings  # pylint: disable=unused-import


@pytest.fixture
def empty_image(image_settings: ImageSettings) -> FloatArray:
    # pylint: disable=missing-function-docstring
    return get_empty_image(image_settings.frames, image_settings.image_pixels)


def test_fill_frame_background(empty_image: FloatArray) -> None:
    """Check that the frame shape is preserved when adding background colour.

    Parameters
    ----------
    empty_image : FloatArray
        Pytest fixture.
    """
    rgb = 0.5, 0.5, 0.75
    frame = 0
    original_shape = empty_image[frame].shape

    filled_frame = fill_frame_background(rgb, empty_image[frame])
    result_shape = filled_frame.shape

    assert original_shape == result_shape


def test_add_object_to_frame(
    image_settings: ImageSettings, empty_image: FloatArray
) -> None:
    """Check that adding an object to an empty image brightens the pixel the
    object is on.

    Parameters
    ----------
    image_settings : ImageSettings
        Pytest fixture.
    empty_image : FloatArray
        Pytest fixture.
    """
    object_row = {"x": 50, "y": 25, "brightness": 0.5, "rgb": (1, 1, 1)}

    frame = 0

    original_rgb_sum = sum(empty_image[frame][:, object_row["x"], object_row["y"]])

    filled_frame = add_object_to_frame(
        object_row,
        empty_image[frame],
        image_settings.area_mesh,
        image_settings.brightness_scale_mesh,
    )

    filled_rgb_sum = sum(filled_frame[:, object_row["x"], object_row["y"]])

    assert filled_rgb_sum > original_rgb_sum


def test_get_scaled_brightness() -> None:
    """Test that brightness scaling works as intended."""
    object_table = QTable({"magnitude": np.random.random_sample((30))})
    get_scaled_brightness(object_table)

    assert min(object_table["brightness"]) == MINIMUM_BRIGHTNESS
    assert max(object_table["brightness"]) == 1

    # minimum magnitude equals maximum brightness and vice versa
    assert np.argmin(object_table["magnitude"]) == np.argmax(object_table["brightness"])
