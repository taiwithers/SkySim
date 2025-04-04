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


@pytest.fixture
def mk_overwriteable():
    """Create temporary files with passed-in names and clean them up later.

    Yields
    ------
    Iterator[Callable[[Path], None]]
        Factory function which does the file creation.
    """
    created_folders = []
    created_files = []

    def _mk_overwriteable(filepath: Path) -> None:
        """Create temporary files to be removed by `mk_overwriteable` later.

        Parameters
        ----------
        filepath : Path
            Path to file to be created/verified.
        """
        parent_exists = filepath.parent.exists()
        file_exists = filepath.exists()

        if not parent_exists:
            created_folders.append(filepath.parent)
            filepath.parent.mkdir(parents=True)

        if not file_exists:
            created_files.append(filepath)
            filepath.touch()

        return

    yield _mk_overwriteable

    for f in created_files:
        if f.exists():
            f.unlink()

    for f in created_folders:
        if f.exists():
            f.rmdir()
