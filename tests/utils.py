"""Utility functions for testing SkySim."""

from pathlib import Path
from typing import Any

from skysim.settings import (
    ImageSettings,
    PlotSettings,
    Settings,
    toml_to_dicts,
)

TEST_ROOT_PATH = Path(__file__).resolve().parent
"""Path to root test suite directory.
"""


ROOT_PATH = TEST_ROOT_PATH.parent
"""Path to root directory containing repository.
"""


def modified_settings_object(
    config_path: Path,
    settings_type: type[Settings | ImageSettings | PlotSettings],
    key: str,
    value: Any,
) -> Any:
    """Create a settings object with a custom attribute (overriding the TOML).
    Return the settings object for further testing.

    Parameters
    ----------
    config_path : Path
        Path to the config file to use.
    settings_type : type[Settings  |  ImageSettings  |  PlotSettings]
        Which type of settings object to create.
    key : str
        The `toml_to_dicts` key to override.
    value : Any
        The value to assign to that key.

    Returns
    -------
    Any
        Value of `attribute`.
    """
    settings_config, image_config, plot_config = toml_to_dicts(config_path)

    if (
        type(settings_type)  # pylint: disable=unidiomatic-typecheck
        == type[ImageSettings]
    ):
        settings = Settings(**settings_config)
        image_config[key] = value
        settings_to_test = settings.get_image_settings(**image_config)

    elif (
        type(settings_type)  # pylint: disable=unidiomatic-typecheck
        == type[PlotSettings]
    ):
        settings = Settings(**settings_config)
        plot_config[key] = value
        settings_to_test = settings.get_plot_settings(**plot_config)

    else:
        settings_config[key] = value
        settings_to_test = Settings(**settings_config)

    return settings_to_test
