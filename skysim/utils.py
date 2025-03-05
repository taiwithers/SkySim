"""Utility functions for SkySim."""

from collections.abc import Collection

import numpy as np
from astropy.table import QTable

# pylint: disable=redefined-builtin,unused-import
from ipdb import set_trace as breakpoint
from numpy.typing import NDArray

type FloatArray = NDArray[np.float64]
type IntArray = NDArray[np.int64]


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
            raise ValueError
    for name, roundto in zip(column_names, decimals):
        table[name] = table[name].round(roundto)

    return table
