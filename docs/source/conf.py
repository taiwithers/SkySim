"""
Configuration for Sphinx.
"""

# disable [W]arning, [C]onvention, and [R]efactoring checks
# pylint: disable=W,C,R

import sys
from pathlib import Path

from skysim.utils import read_pyproject

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
pyproject = read_pyproject()

project = pyproject["name"]
get_name = lambda authstr: authstr[: authstr.index("<")].strip()
author = ", ".join([get_name(auth) for auth in pyproject["authors"]])
copyright = (
    f" %Y, {author}"  # If you remove the space in front of %Y it defaults to 1980
)
release = pyproject["version"]
version = release  # major version only
language = "en"


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = []
suppress_warnings = []

templates_path = ["_templates"]
exclude_patterns = []

default_role = "py:obj"  # interpret `function` as crossref to the function 'function'

# -- Python Domain Options ---------------------------------------------------

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_theme_options = {
    "footer_start": ["pydatasourcelink", "copyright"],
    "footer_end": ["sphinx-version", "theme-version"],
    "secondary_sidebar_items": ["page-toc"],
    "github_url": pyproject["urls"]["repository"],
    "header_links_before_dropdown": 2,
}
html_sidebars = {"**": ["sidebar-nav-bs"]}
html_sidebars.update(
    {pagename: [] for pagename in ["usage", "api/index", "examples/index", "devnotes"]}
)  # pages on which to hide the primary sidebar
html_sourcelink_suffix = ""
html_title = f"{project} {release}"
html_short_title = project
html_css_files = ["css/custom.css"]


# -- Extension settings ------------------------------------------------------


## autodoc
extensions.append("sphinx.ext.autodoc")
sys.path.insert(0, str(Path("..", "..").resolve()))
autodoc_typehints = "none"  # napoleon deals with these
autodoc_member_order = "groupwise"
autodoc_default_options = {"members": True}
# autodoc_undoc_members = False


## autodoc_pydantic
extensions.append("sphinxcontrib.autodoc_pydantic")
autodoc_pydantic_model_show_json = False
# autodoc_pydantic_model_undoc_members = False


## autosummary
extensions.append("sphinx.ext.autosummary")
autosummary_generate = True


## intersphinx
extensions.append("sphinx.ext.intersphinx")
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "astropy": ("https://docs.astropy.org/en/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
    "timezonefinder": ("https://timezonefinder.readthedocs.io/en/latest/", None),
    "astroquery": ("https://astroquery.readthedocs.io/en/latest/", None),
}


# MyST
extensions.append("myst_parser")
myst_links_external_new_tab = True
suppress_warnings.append("myst.header")
myst_heading_anchors = 2  # create linkable headings up to this depth
myst_enable_extensions = ["attrs_inline"]


## napoleon
extensions.append("sphinx.ext.napoleon")
napoleon_use_rtype = False  # put return types inline
napoleon_preprocess_types = True
napoleon_use_param = True  # default, required for napoleon_type_aliases
napoleon_type_aliases = {
    # ~ means only the final element is shown in the link name
    # types defined in skysim
    "Settings": "~skysim.settings.Settings",
    "PlotSettings": "~skysim.settings.PlotSettings",
    "ImageSettings": "~skysim.settings.ImageSettings",
    "FloatArray": "~skysim.utils.FloatArray",
    "IntArray": "~skysim.utils.IntArray",
    "ConfigMapping": "~skysim.settings.ConfigMapping",
    "ConfigValue": "~skysim.settings.ConfigValue",
    "TOMLConfig": "~skysim.settings.TOMLConfig",
    "RGBTuple": "~skysim.colours.RGBTuple",
    "InputColour": "~skysim.colours.InputColour",
    # python
    "Collection": "~collections.abc.Collection",
    "datetime": "~datetime.datetime",
    "Mapping": "~collections.abc.Mapping",
    "Path": "~pathlib.Path",
    "time": "~datetime.time",
    "timedelta": "~datetime.timedelta",
    "ZoneInfo": "~zoneinfo.ZoneInfo",
    # other libraries
    ## astropy
    "EarthLocation": "astropy.coordinates.EarthLocation",
    "QTable": "astropy.table.QTable",
    "Row": "astropy.table.Row",
    "SkyCoord": "astropy.coordinates.SkyCoord",
    "Table": "astropy.table.Table",
    "Time": "astropy.time.Time",
    "WCS": "astropy.wcs.WCS",
    ## matplotlib
    "Axes": "matplotlib.axes.Axes",
    "LinearSegmentedColormap": "matplotlib.colors.LinearSegmentedColormap",
    ## numpy
    "ArrayLike": "numpy.typing.ArrayLike",  # links to np.typing don't work
    ## pydantic, links don't work?
    "NonNegativeFloat": "pydantic.NonNegativeFloat",
    "PositiveFloat": "pydantic.PositiveFloat",
    "PositiveInt": "pydantic.PositiveInt",
    "ValidationInfo": "pydantic.ValidationInfo",
}


## ViewCode
extensions.append("sphinx.ext.viewcode")
viewcode_line_numbers = True
