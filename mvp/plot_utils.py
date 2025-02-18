import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.visualization import wcsaxes
from matplotlib.axes import Axes
from matplotlib.colors import ListedColormap
from matplotlib.font_manager import FontProperties
from matplotlib import ticker

# from .cloud import CLOUD_DISTANCES
cloud_freespace = {'MonR1': 'bottom left', 'MonR2': 'top left', 'M16': 'top left', 'NGC2264': 'bottom right',
                   'W3_Main': 'bottom right', 'W3_West': 'top right', 'NGC7538': 'top right', 'Rosette': 'top right',
                   'M17': 'bottom left', 'W48': 'top left', 'CygnusX_N': 'bottom left', 'CygnusX_S': 'top left'}

COLUMN_WIDTH = 3.35

nc_colours = ['lightgrey', '#88CCEE', '#AA4499', '#117733']
nc_cmap = ListedColormap(nc_colours)
cluster_colour = 'indianred'
legend_kwargs = dict(borderaxespad=.1,  # outside border
                     borderpad=.4,  # inside border
                     framealpha=.8,
                     # labelspacing=.1,
                     handlelength=1, fancybox=False,
                     edgecolor='k')

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 12
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Computer Modern Roman', 'CMU Serif']
plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['text.latex.preamble'] = '\\usepackage{amsmath}'

# relative font sizes
plt.rcParams['axes.labelsize'] = 'small'
plt.rcParams['legend.fontsize'] = 'small'
plt.rcParams['xtick.labelsize'] = 'small'
plt.rcParams['ytick.labelsize'] = 'small'
cbar_labelsize = 'small'
textSizes = ['small', 'x-small', 'xx-small']

plt.rcParams['xtick.major.size'] = 5
plt.rcParams['xtick.major.width'] = 1.2
plt.rcParams['ytick.major.size'] = 5
plt.rcParams['ytick.major.width'] = 1.2

plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['savefig.dpi'] = 500

plt.rcParams['figure.figsize'] = 10, 8
plt.rcParams['image.origin'] = 'lower'

class CustomLogLocator(ticker.Locator):

    def __init__(self):
        return

    def __call__(self):
        """Return the locations of the ticks."""
        vmin, vmax = self.axis.get_view_interval()
        return self.tick_values(vmin, vmax)

    def tick_values(self, tmin, tmax):
        emin, emax = np.floor(np.log10([tmin,tmax]))
        if emax-emin > 2:
            return [10**i for i in range(int(emin), int(emax)+1)]

        potential_ticks = []
        for exp in range(int(emin), int(emax)+1):
            for coeff in range(1,10):
                potential_ticks.append(coeff*10**exp)
        potential_ticks = np.array(potential_ticks).astype(float)
        potential_ticks = potential_ticks[tmin<=potential_ticks]
        potential_ticks = potential_ticks[potential_ticks<=tmax]
        if len(potential_ticks) < 4: return potential_ticks

        ticks = [potential_ticks[0]]
        for tick in potential_ticks[1:-1]:
            if np.log10(tick)%1 == 0:
                ticks.append(tick)
        ticks.append(potential_ticks[-1])
        return ticks

class CustomLogFormatter(ticker.Formatter):
    def __init__(self, no_exponents=False):
        self.no_exponents = no_exponents

    def __call__(self, value, pos=None):
        exponent = np.floor(np.log10(value))
        coeff = value / 10**exponent
        if coeff != 1: return f'${coeff:.0f}\\times 10^{{{exponent:.0f}}}$'
        else: return f'$10^{{{exponent:.0f}}}$'


def print_limits(ax):
    print(f'xlim={ax.get_xlim()}\tylim={ax.get_ylim()}')

def fig_setup(figsize=None, fig_only=False, wcs=None, fig_kwargs={}, plot_kwargs={}, **kwargs):
    if figsize is None:
        figsize = (COLUMN_WIDTH, COLUMN_WIDTH)

    if fig_only:
        return plt.figure(figsize=figsize, **kwargs)
    if wcs is None:
        return plt.subplots(figsize=figsize, **kwargs)
    else:
        if kwargs: # kwargs is not the empty dict
            raise Exception("When using WCS, fig_kwargs and plot_kwargs should be provided instead of **kwargs.")
        fig = plt.figure(figsize=figsize, **fig_kwargs)
        ax = plt.subplot(projection=wcs, **plot_kwargs)
        fig.add_axes(ax)
        return fig, ax

def save_fig(figure, title, directory=None, filetype='png', cloud=None, keep_open=False):
    if directory is None: directory = os.getcwd()
    savename = f'{directory}/{title.replace(" ", "_")}'
    if '.' not in savename[-5:]:
        savename = f'{savename}.{filetype}'
    figure.savefig(savename)

    msg = f'{savename} saved.'
    if cloud is not None: cloud.logger.info(msg)
    else: print(msg)

    if not keep_open: plt.close(fig=figure)

def cloud_save_fig(cloud, fname, tries=3):
    saved = False
    while (tries > 0) and (not saved):
        tries = - 1
        try:
            plt.savefig(fname)
            plt.close()
            cloud.logger.info(f'{fname} saved.')
            saved = True
        except SyntaxError:
            pass
    if not saved:
        cloud.logger.error(f'{fname} could not be saved, please try again.')

def style_wcs_axes(ax, axis_label=(True, True), axis_ticks=(True, True), ylabelpad=1):
    ax_x, ax_y = ax.coords

    if axis_label[0]:
        ax_x.set_axislabel('Right Ascension')
    else:
        ax_x.set_auto_axislabel(False)

    if axis_label[1]:
        ax_y.set_axislabel('Declination', minpad=ylabelpad)
    else:
        ax_y.set_auto_axislabel(False)

    if axis_ticks[0]:
        ax_x.set_ticks_position('b')
        ax_x.set_ticklabel(exclude_overlapping=True)
    else:
        ax_x.set_ticks_visible(False)
        ax_x.set_ticklabel_visible(False)

    if axis_ticks[1]:
        ax_y.set_ticks_position('l')
    else:
        ax_y.set_ticks_visible(False)
        ax_y.set_ticklabel_visible(False)

    return ax

def add_scalebar(cloud_name, ax, hdr, location=None, angular_size=5*u.arcmin):
    if location is None:
        location = 'bottom right'
    u.set_enabled_equivalencies(u.dimensionless_angles())
    if cloud_name not in CLOUD_DISTANCES.keys():
        cloud_name = cloud_name[:cloud_name.rindex('_')]
    arcmin_per_pc = np.tan(
        1*u.pc / (CLOUD_DISTANCES[cloud_name][0]*u.kpc)).to(u.arcmin)
    scalebar_length = angular_size/arcmin_per_pc * u.pc
    wcsaxes.add_scalebar(ax, angular_size, corner=location, color='k', frame=True,
                         pad=.5,  # inside border
                         borderpad=.2,  # outside border
                         label=f'{angular_size.value:.0f}$^\\prime$ = {scalebar_length.value:.2f} pc',
                         fontproperties=FontProperties(size=textSizes[2]))

    pixel_size = abs(hdr['CDELT1'])*u.Unit(hdr['CUNIT1'])
    pixels_in_scalebar = angular_size.to(
        u.arcsecond) / pixel_size.to(u.arcsecond)
    return ax
    # print(f'{pixels_in_scalebar=:.2f}\t{scalebar_length=:.2f}')

def add_colorbar(im, cbar_thickness=None, cbar_pad=None, fig=None, ax=None, label=None, labelpad=None, labelsize=cbar_labelsize ,**cbar_kwargs):
    # https://stackoverflow.com/a/76378778
    if ax is None:
        ax = im.axes
    if fig is None:
        fig = ax.figure

    if isinstance(ax, Axes):
        ax_left, ax_bottom, ax_width, ax_height = ax.get_position().bounds
    else:
        ax_left, ax_bottom, ax_width, ax_height = 0, 0, 1, 1
    if 'location' not in cbar_kwargs:
        cbar_kwargs['location'] = 'right'

    if cbar_kwargs['location'] == 'right':
        if cbar_thickness is None:
            cbar_thickness = .07 * ax_width
        if cbar_pad is None:
            cbar_pad = cbar_thickness

        cbar_left = ax_left + ax_width + 2.5*cbar_pad
        cbar_ax = fig.add_axes(
            [cbar_left, ax_bottom, cbar_thickness, ax_height])

    elif cbar_kwargs['location'] == 'left':
        if cbar_thickness is None:
            cbar_thickness = .07 * ax_width
        if cbar_pad is None:
            cbar_pad = cbar_thickness

        cbar_left = ax_left - 2.5*cbar_pad
        cbar_ax = fig.add_axes(
            [cbar_left, ax_bottom, cbar_thickness, ax_height])

    elif cbar_kwargs['location'] == 'top':
        if cbar_thickness is None:
            cbar_thickness = .07 * ax_height
        if cbar_pad is None:
            cbar_pad = cbar_thickness

        cbar_bottom = ax_bottom + ax_height + 2.5*cbar_pad
        cbar_ax = fig.add_axes(
            [ax_left, cbar_bottom, ax_width, cbar_thickness])

    cbar = fig.colorbar(im, cax=cbar_ax, **cbar_kwargs)
    if label is not None:
        cbar.set_label(label, labelpad=labelpad, size=labelsize)

    return cbar

def square_contours(ax, contour_data, precision=10, filled=False, **contour_kwargs):
    fX, fY = np.array(np.meshgrid(
        np.arange(0, contour_data.shape[1]*precision), np.arange(0, contour_data.shape[0]*precision))).astype(float)/precision
    fine = np.empty(precision*np.array(contour_data.shape))

    for (y, x), nc in np.ndenumerate(contour_data):
        fy, fx = precision*y, precision*x
        fine[fy:fy+precision, fx:fx+precision] = nc
    fX -= (precision-1)/(2*precision)
    fY -= (precision-1)/(2*precision)
    if filled:
        return ax.contourf(fX, fY, fine, **contour_kwargs)
    return ax.contour(fX, fY, fine, **contour_kwargs)

def set_contour_labels(contours, labels):

    if isinstance(contours, list):
        handles = [c.legend_elements()[0] for c in contours]
        if isinstance(handles[0], list):
            handles = [sublist[0] for sublist in handles]
    else:
        handles = contours.legend_elements()[0]

    for i, l in enumerate(labels):
        handles[i].set_label(l)
    return handles[:len(labels)]

def transfer_axes(ax, new_figure, old_figure=None, subplot_id=111, sharex=None, sharey=None):
    # https://gist.github.com/salotz/8b4542d7fe9ea3e2eacc1a2eef2532c5
    ax.remove()
    ax.figure = new_figure
    new_figure.axes.append(ax)
    new_figure.add_axes(ax, sharex=sharex, sharey=sharey)

    pos_ax = new_figure.add_subplot(subplot_id)
    ax.set_position(pos_ax.get_position())
    pos_ax.remove()

    if old_figure is not None:
        plt.close(old_figure)

    return new_figure, ax

def get_logspace_bins(values, percentiles=[0,100], N=50):
    values = values[values>0]
    low, high = np.log10(np.nanpercentile(values, percentiles))
    return np.logspace(np.floor(low), np.ceil(high), N)

def modify_histogram(histogram, *dataset_dictionaries):
    counts, bins, patches = histogram

    for patch, kwargs in zip(patches, dataset_dictionaries):
        if isinstance(patch, list):
            patch[0].set(**kwargs)
        else:
            patch.set(**kwargs)

def add_diagonal(ax, slope=1, intercept=0, log=True, thickness=0, relative_thickness=False, **plot_kwargs):
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    points = np.array([min(xlim[0],ylim[0]), max(xlim[1],ylim[1])])
    xvals = np.linspace(*points)

    if log: yvals = 10** (slope*np.log10(xvals)+intercept)
    else: yvals = slope*xvals+intercept

    if thickness == 0:
        ax.plot(xvals, yvals, **plot_kwargs)
    else:
        thickness /= 2
        if relative_thickness:
            lower = yvals/thickness
            upper = yvals*thickness
        else:
            lower = yvals - thickness
            upper = yvals + thickness
        ax.fill_between(xvals, lower, upper, **plot_kwargs)
    ax.set(xlim=xlim,ylim=ylim)
    return ax

def add_line(ax, orientation, **kwargs):
    if orientation == 'd':
        return add_diagonal(ax, **kwargs)
    if orientation == 'h':
        if 'thickness' in kwargs:
            thickness = kwargs.pop('thickness')/2
            y_centre = kwargs.pop('y')
            ymin = y_centre - thickness
            ymax = y_centre + thickness
            return ax.axhspan(ymin, ymax **kwargs)
        else:
            return ax.axhline(y=kwargs.pop('y'), **kwargs)
    if orientation == 'v':
        if 'thickness' in kwargs:
            thickness = kwargs.pop('thickness')/2
            x_centre = kwargs.pop('x')
            xmin = x_centre - thickness
            xmax = x_centre + thickness
            return ax.axvspan(xmin, xmax **kwargs)
        else:
            return ax.axvline(x=kwargs.pop('x'), **kwargs)

def get_print_name(cloud_name):
    cloud_name = cloud_name.replace('CygnusX', 'Cygnus X')
    cloud_name = cloud_name.replace('_S', '_South')
    cloud_name = cloud_name.replace('_N', '_North')
    cloud_name = cloud_name.replace('_', ' ')
    cloud_name = cloud_name.replace('NGC', 'NGC ')
    return cloud_name

def get_percentiles(data, ignore_nan=True, coverage=90):
    minimum = (100-coverage)/2
    maximum = 100 - minimum

    if ignore_nan:
        return np.nanpercentile(data, [minimum, maximum])
    return np.percentile(data, [minimum, maximum])

def get_lim_from_image(data, border=1):
    xdata = np.nansum(data, axis=0)
    ydata = np.nansum(data, axis=1)

    borderpad = border * np.array([-1,1])

    xlim = np.nonzero(xdata)[0][[0,-1]] + borderpad
    ylim = np.nonzero(ydata)[0][[0,-1]] + borderpad

    return xlim, ylim

def format_unit(astropy_unit, brackets=True):
    if astropy_unit == (u.M_sun * (u.K * u.km/u.s)**-1):
        mass = u.M_sun.to_string(format='latex_inline')
        ii = (u.K*u.km/u.s).to_string(format='latex_inline')
        string = f'${mass[1:-1]} \\left({ii[1:-1]}\\right)^{{-1}}$'
    else:
        string = astropy_unit.to_string(format='latex_inline')
    if brackets: return f'$\\left({string[1:-1]}\\right)$'
    return string
