"""Plotting module for SkySim. Combines a `numpy` array of RGB values from
`skysim.populate` with the `PlotSettings` plotting configuration.
"""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

import subprocess
from collections.abc import Collection
from pathlib import Path

import numpy as np
from astropy.visualization.wcsaxes.frame import EllipticalFrame
from astropy.wcs import WCS
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from skysim.settings import PlotSettings
from skysim.utils import TEMPFILE_SUFFIX, FloatArray, get_tempfile_path

# Methods


## Top-Level Plot Method


def create_plot(
    plot_settings: PlotSettings, image_matrix: FloatArray, verbose_level: int
) -> None:
    """Main function for this module, creates image files from `image_matrix`.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    image_matrix : FloatArray
        RGB images.
    verbose_level : int
        How much detail to print.
    """
    if plot_settings.frames == 1:
        create_single_plot(plot_settings, image_matrix, verbose_level)

    else:
        create_multi_plot(plot_settings, image_matrix, verbose_level)

    return


## Secondary Plot Methods


def create_single_plot(
    plot_settings: PlotSettings, image_matrix: FloatArray, verbose_level: int
) -> None:
    """Plotting function for a still image.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    image_matrix : FloatArray
        Single frame RGB image.
    verbose_level : int
        How much detail to print.
    """
    save_frame(0, plot_settings, image_matrix[0], plot_settings.filename)
    if verbose_level > 0:
        print(f"{plot_settings.filename} saved.")
    return


def create_multi_plot(
    plot_settings: PlotSettings, image_matrix: FloatArray, verbose_level: int
) -> None:
    """Plotting function for creating a video.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration object, passed to `save_frame`.
    image_matrix : FloatArray
        Multi-frame RGB image.
    verbose_level : int
        How much detail to print.
    """

    # create the temporary directory
    if not plot_settings.tempfile_path.is_dir():
        try:
            plot_settings.tempfile_path.mkdir()
        except PermissionError as e:
            raise ValueError(
                "Permission denied creating temporary directory for storing "
                f"intermediate data products ({plot_settings.tempfile_path}). "
                "Choose a different path for the output file."
            ) from e

    # create all the frames
    results = []
    for i in range(plot_settings.frames):
        tempfile_path = get_tempfile_path(plot_settings, i)
        results.append(save_frame(i, plot_settings, image_matrix[i], tempfile_path))
        if verbose_level > 1:
            print(f"{tempfile_path} saved.")

    # convert frames into a movie
    ffmpeg_call = construct_ffmpeg_call(plot_settings)
    if verbose_level > 1:
        print(f"Running ffmpeg with `{ffmpeg_call}`")
    ffmpeg_return_code = run_ffmpeg(ffmpeg_call)
    if ffmpeg_return_code == 0:
        if verbose_level > 0:
            print(f"{plot_settings.filename} saved.")

    movie_cleanup([i[1] for i in results], plot_settings.tempfile_path, verbose_level)

    return


## Generic Helper Methods


def save_frame(
    index: int, plot_settings: PlotSettings, frame: FloatArray, filename: Path
) -> tuple[int, Path]:
    """Create and save a figure for a single frame.

    Parameters
    ----------
    index : int
        Index of the frame.
    plot_settings : PlotSettings
        Configuration object. Attributes accessed are `figure_size`,
        `wcs_objects`, `observation_info`, `datetime_strings`, and `dpi`.
    frame : FloatArray
        RGB image.
    filename : Path
        Location to save the image.

    Returns
    -------
    tuple[int, str]
        Index and filename.
    """
    fig, ax = plt.subplots(
        figsize=plot_settings.figure_size,
        subplot_kw={
            "frame_on": False,
            "projection": plot_settings.wcs_objects[index],
            "frame_class": EllipticalFrame,
        },
    )

    ax.set(xticks=[], yticks=[])
    fig.suptitle(plot_settings.observation_info)
    display_frame(
        ax,
        plot_settings.wcs_objects[index],
        frame,
        plot_settings.datetime_strings[index],
    )

    try:
        plt.savefig(
            filename,
            dpi=plot_settings.dpi,
            bbox_inches="tight",
        )
    except PermissionError as e:
        raise ValueError(
            f"Permission denied saving image ({filename}). "
            "Choose a different path for the output file."
        ) from e
    plt.close()

    return (index, filename)


def display_frame(ax: Axes, wcs: WCS, frame: FloatArray, frame_title: str) -> Axes:
    """Display a single frame on a matplotlib axes.

    Parameters
    ----------
    ax : Axes
        Axes to use.
    wcs : WCS
        Coordinates of the new frame.
    frame : FloatArray
        RGB image.
    frame_title : str
        Title of the frame.

    Returns
    -------
    Axes
        Updated axes.
    """
    ax.reset_wcs(wcs)

    ax.imshow(frame, origin="lower")

    # axis labels
    for axis in ax.coords:
        axis.set_auto_axislabel(False)
        axis.set_ticks_visible(False)
        axis.set_ticklabel_visible(False)

    # frame
    ax.coords.frame.set_linewidth(0)

    ax.set_title(frame_title, backgroundcolor="w", pad=8)

    return ax


## Movie-Specific Helper Methods


def construct_ffmpeg_call(plot_settings: PlotSettings) -> str:
    """Construct the command to call ffmpeg with. Note that the command is not
    actually run.
    Note that the ffmpeg flag `-pix_fmt yuv420p` is required in order for most players,
    and yuv420p also requires that the pixel dimensions of the movie be divisible by 2.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration. Attributes accessed are `figure_size`, `dpi`, `fps`,
        `tempfile_path`, `tempfile_zfill`, and `filename`.

    Returns
    -------
    str
        Command to run.
    """

    # create a filter to make the output have pixel dimensions divisible by 2
    output_pixels = np.ceil(max(plot_settings.figure_size) * plot_settings.dpi).astype(
        int
    )
    if output_pixels % 2 != 0:
        output_pixels += 1
    output_filter = (
        "-filter_complex "
        '"'
        f"scale={output_pixels}:{output_pixels}:force_original_aspect_ratio=decrease,"
        f"pad={output_pixels}:{output_pixels}:(ow-iw)/2:(oh-ih)/2"
        '"'
    )

    global_options = "-loglevel warning -hide_banner"
    input_options = f"-framerate {plot_settings.fps}"
    input_files = f"{plot_settings.tempfile_path}/%0{plot_settings.tempfile_zfill}d.png"
    output_options = (
        f"-y -r {plot_settings.fps} -codec:v libx264 {output_filter} -pix_fmt yuv420p"
    )
    return (
        f"ffmpeg {global_options} {input_options} -i {input_files} {output_options}"
        f" {plot_settings.filename}"
    )


def run_ffmpeg(ffmpeg_call: str) -> int:
    """Run FFmpeg to convert the set of images into a video.

    Parameters
    ----------
    ffmpeg_call : str
        The shell command to run FFmpeg.

    Returns
    -------
    int
        FFmpeg return code.

    Raises
    ------
    ValueError
        Raised if FFmpeg returns a non-zero exit code.
    """
    ffmpeg_out = subprocess.run(
        ffmpeg_call,
        shell=True,  # run as shell command
        capture_output=True,  # adds stderr and stdout attributes
        text=True,  # interpret stderr and stdout as text
        check=False,  # don't raise exception on non-zero exit code
    )
    if ffmpeg_out.returncode != 0:
        raise ValueError(
            "Something went wrong compiling the frames into a video. "
            f"FFmpeg error: {ffmpeg_out.stderr}"
        )

    return ffmpeg_out.returncode


def movie_cleanup(
    filenames: Collection[Path], directory: Path, verbose_level: int
) -> None:
    """Clean up the tempfiles used in creating a video.

    Parameters
    ----------
    filenames : Collection[Path]
        The image files to delete.
    directory : Path
        The directory to delete.
    verbose_level : int
        How much detail to print.

    Raises
    ------
    ValueError
        Raised if the directory cannot be deleted.
    """
    # remove all the tempfiles
    for path in filenames:
        if path.suffix == TEMPFILE_SUFFIX:
            path.unlink()
            if verbose_level > 1:
                print(f"{path} removed.")

    # remove the tempfile directory
    try:
        if verbose_level > 1:
            print(f"{directory} removed.")
        directory.rmdir()
    except OSError as e:
        raise ValueError(
            f"Can't remove temporary directory {directory}. {e.strerror}"
        ) from e
