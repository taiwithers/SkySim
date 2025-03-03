# pylint: disable=missing-module-docstring
from skysim.settings import load_from_toml


def main() -> None:
    # pylint: disable=missing-function-docstring
    image_settings, plot_settings = load_from_toml(
        "/home/taiwithers/projects/skysim/tests/minimal.toml"
    )
    print(image_settings, plot_settings)
