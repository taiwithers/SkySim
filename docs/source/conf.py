"""
Configuration for Sphinx.
"""

# disable [W]arning, [C]onvention, and [R]efactoring checks
# pylint: disable=W,C,R

import os
import sys
import tomllib
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
pyproject = tomllib.load(open(Path("../../pyproject.toml"), "rb"))["tool"]["poetry"]

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
sys.path.insert(0, str(Path("..", "..").resolve()))

extensions = []
suppress_warnings = []

templates_path = ["_templates"]
exclude_patterns = []

# -- Python Domain Options ---------------------------------------------------
add_module_names = False  # hide the module name in the signature line for objects


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": pyproject["urls"]["repository"],  # required
            # Icon class (if "type": "fontawesome"), or path to local image (if "type": "local")
            "icon": "fa-brands fa-square-github",
            # The type of image to be used
            "type": "fontawesome",
        }
    ]
}
html_short_title = project


# -- Extension settings ------------------------------------------------------


## autodoc
extensions.append("sphinx.ext.autodoc")
autodoc_typehints = "none"  # napoleon deals with these
autodoc_member_order = "groupwise"
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
}


# MyST
extensions.append("myst_parser")
myst_links_external_new_tab = True
suppress_warnings.append("myst.xref_missing")


## napoleon
extensions.append("sphinx.ext.napoleon")
napoleon_use_rtype = False  # put return types inline
napoleon_preprocess_types = True


## ViewCode
extensions.append("sphinx.ext.viewcode")
viewcode_line_numbers = True
