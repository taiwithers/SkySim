"""Fixtures for the entire tests/ folder."""

from pathlib import Path

import pytest

from skysim.settings import (
    ImageSettings,
    PlotSettings,
    Settings,
    load_from_toml,
)

from .utils import TEST_ROOT_PATH


@pytest.fixture(scope="session", params=["still_image", "movie"])
def config_path(request: pytest.FixtureRequest) -> Path:
    # pylint: disable=missing-function-docstring
    return Path(f"{TEST_ROOT_PATH}/configs/{request.param}.toml")


@pytest.fixture(scope="session")
def settings(config_path: str) -> Settings:
    # pylint: disable=missing-function-docstring
    return load_from_toml(config_path, return_settings=True)


@pytest.fixture(scope="session")
def image_settings(config_path: str) -> ImageSettings:
    # pylint: disable=missing-function-docstring
    return load_from_toml(config_path)[0]


@pytest.fixture(scope="session")
def plot_settings(config_path: str) -> PlotSettings:
    # pylint: disable=missing-function-docstring
    return load_from_toml(config_path)[1]
