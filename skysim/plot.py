"""Plotting module for SkySim."""

from astropy.visualization.wcsaxes.frame import EllipticalFrame
from astropy.wcs import WCS
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from .settings import PlotSettings
from .utils import FloatArray


def create_plot(plot_settings: PlotSettings, image_matrix: FloatArray) -> None:
    """Main function for this module, creates image files from `image_matrix`.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.
    image_matrix : FloatArray
        RGB images.
    """
    fig, ax = plt.subplots(
        figsize=plot_settings.figure_size,
        subplot_kw={
            "frame_on": False,
            "projection": plot_settings.wcs_objects[0],
            "frame_class": EllipticalFrame,
        },
    )

    ax.set(xticks=[], yticks=[])
    fig.suptitle(plot_settings.observation_info)

    for i in range(plot_settings.frames):
        ax = display_frame(
            ax,
            plot_settings.wcs_objects[i],
            image_matrix[i],
            plot_settings.datetime_strings[i],
        )
        plt.savefig(
            f"{plot_settings.filename}_{i}",
            dpi=plot_settings.dpi,
            bbox_inches="tight",
        )
    return


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

    ax.imshow(frame)

    # axis labels
    for axis in ax.coords:
        axis.set_auto_axislabel(False)
        axis.set_ticks_visible(False)
        axis.set_ticklabel_visible(False)

    # frame
    ax.coords.frame.set_linewidth(0)

    ax.set_title(frame_title, backgroundcolor="w", pad=8)

    return ax
