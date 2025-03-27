"""Utility functions for SkySim."""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

from collections.abc import Collection
from pathlib import Path
from typing import ForwardRef  # pylint: disable=unused-import

import numpy as np
from astropy.table import QTable
from numpy.typing import NDArray

# Type Aliases

type FloatArray = NDArray[np.float64]
type IntArray = NDArray[np.int64]


# Constants


TEMPFILE_SUFFIX = ".png"
"""File extension to use for video frames."""


# Methods


def round_columns(
    table: QTable,
    column_names: Collection[str] = ("ra", "dec", "magnitude"),
    decimals: int | Collection[int] = 5,
) -> QTable:
    """
    Round columns of an Astropy Table.

    Parameters
    ----------
    table : Table
        Table.
    column_names : list[str], optional
        Names of columns to be rounded, by default ["ra","dec","magnitude"].
    decimals : int|list[int], optional
        Number of decimal places to keep, can be list of ints (same size as
        `column_names`) or a single value, by default 5.

    Returns
    -------
    Table
        `table` with `column_names` rounded to `decimals`.
    """

    if isinstance(decimals, int):
        decimals = [decimals] * len(column_names)
    else:
        if len(decimals) != len(column_names):
            raise ValueError(
                f"{len(column_names)} columns were given to be rounded, but "
                f"{len(decimals)} values were given as decimal points to round to."
            )
    for name, roundto in zip(column_names, decimals):
        table[name] = table[name].round(roundto)

    return table


def get_tempfile_path(
    plot_settings: "PlotSettings", frame_index: int  # type: ignore[name-defined]
) -> Path:
    """Get the path for a temporary file that ffmpeg will read an image from.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    frame_index : int
        Which frame.

    Returns
    -------
    Path
        Path.
    """
    return (
        plot_settings.tempfile_path
        / f"{str(frame_index).zfill(plot_settings.tempfile_zfill)}{TEMPFILE_SUFFIX}"
    )
