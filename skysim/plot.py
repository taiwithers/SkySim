"""Plotting module for SkySim."""

import subprocess
from collections.abc import Collection
from pathlib import Path

import numpy as np
from astropy.visualization.wcsaxes.frame import EllipticalFrame
from astropy.wcs import WCS
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from skysim.settings import PlotSettings
from skysim.utils import FloatArray

# Constants


TEMPFILE_SUFFIX = ".png"
"""File extension to use for video frames."""


# Methods


## Top-Level Plot Method


def create_plot(plot_settings: PlotSettings, image_matrix: FloatArray) -> None:
    """Main function for this module, creates image files from `image_matrix`.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    image_matrix : FloatArray
        RGB images.
    """
    if plot_settings.frames == 1:
        create_single_plot(plot_settings, image_matrix)

    else:
        create_multi_plot(plot_settings, image_matrix)

    return


## Secondary Plot Methods


def create_single_plot(plot_settings: PlotSettings, image_matrix: FloatArray) -> None:
    """Plotting function for a still image.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    image_matrix : FloatArray
        Single frame RGB image.
    """
    save_frame(0, plot_settings, image_matrix[0], plot_settings.filename)
    print(f"{plot_settings.filename} saved.")
    return


def create_multi_plot(plot_settings: PlotSettings, image_matrix: FloatArray) -> None:
    """Plotting function for creating a video.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    image_matrix : FloatArray
        Multi-frame RGB image.
    """
    if not plot_settings.tempfile_path.is_dir():
        plot_settings.tempfile_path.mkdir()

    results = []
    for i in range(plot_settings.frames):
        results.append(
            save_frame(
                i,
                plot_settings,
                image_matrix[i],
                plot_settings.tempfile_path
                / f"{str(i).zfill(plot_settings.tempfile_zfill)}.png",
            )
        )

    run_ffmpeg(plot_settings)
    movie_cleanup([i[1] for i in results], plot_settings.tempfile_path)

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
        Configuration.
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

    plt.savefig(
        filename,
        dpi=plot_settings.dpi,
        bbox_inches="tight",
    )
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
    """Construct the command to call ffmpeg with.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.

    Returns
    -------
    str
        Command to run.
    """
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
    return f"ffmpeg {global_options} {input_options} -i {input_files} {output_options} {plot_settings.filename}"


def run_ffmpeg(plot_settings: PlotSettings) -> None:
    """Run FFmpeg to convert the set of images into a video.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.

    Raises
    ------
    ValueError
        Raised if FFmpeg returns a non-zero exit code.
    """
    ffmpeg_call = construct_ffmpeg_call(plot_settings)
    print(f"Running ffmpeg with `{ffmpeg_call}`")
    ffmpeg_out = subprocess.run(
        ffmpeg_call,
        shell=True,  # run as shell command
        capture_output=True,  # adds stderr and stdout attributes
        text=True,  # interpret stderr and stdout as text
        check=False,  # don't raise exception on non-zero exit code
    )
    if ffmpeg_out.returncode == 0:
        print(f"{plot_settings.filename} saved.")
    else:
        raise ValueError(
            f"Something went wrong compiling the frames into a video. FFmpeg error: {ffmpeg_out.stderr}"
        )


def movie_cleanup(filenames: Collection[Path], directory: Path) -> None:
    """Clean up the tempfiles used in creating a video.

    Parameters
    ----------
    filenames : Collection[Path]
        The image files to delete.
    directory : Path
        The directory to delete.

    Raises
    ------
    ValueError
        Raised if the directory cannot be deleted.
    """
    for path in filenames:
        if path.suffix == TEMPFILE_SUFFIX:
            path.unlink()
    try:
        directory.rmdir()
    except OSError as e:
        raise ValueError(
            f"Can't remove temporary directory {directory}. {e.strerror}"
        ) from e
