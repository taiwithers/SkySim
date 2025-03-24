"""Class and functions for colour management."""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

from collections.abc import Collection
from typing import Any

from matplotlib.colors import to_rgb
from pydantic import computed_field
from pydantic.dataclasses import dataclass

# Type Aliases

type RGBTuple = tuple[float, float, float]
type InputColour = list[float | int] | str


@dataclass
class RGB:  # type: ignore[misc]
    """Tuple of RGB values."""

    original: InputColour
    """Whatever was passed to the constructor."""

    @computed_field()
    @property
    def rgb(self) -> RGBTuple:
        """Generate an rgb tuple with values [0,1].

        Returns
        -------
        RGBTuple
            RGB value.
        """
        if (
            isinstance(self.original, Collection)
            and not isinstance(self.original, str)
            and (len(self.original) in (3, 4))
            and any(i > 1 for i in self.original)
        ):
            self.original = list(i / 255 for i in self.original)
        return to_rgb(self.original)  # type: ignore[arg-type]


def convert_colour(colour: Any) -> RGBTuple:
    # pylint: disable=missing-function-docstring
    return RGB(colour).rgb
