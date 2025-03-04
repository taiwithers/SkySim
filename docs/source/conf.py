"""
Configuration for Sphinx.
"""

import sys
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "SkySim"
copyright = "2025, Tai Withers"
author = "Tai Withers"
release = "0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
sys.path.insert(0, str(Path("..", "..", f"{project.lower()}").resolve()))

extensions = []

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]


# -- Extension settings ------------------------------------------------------


## autoapi
extensions.append("autoapi.extension")
autoapi_dirs = ["../../skysim"]
autoapi_root = "autoapi"  # under docs/build/doctrees
autoapi_generate_api_docs = False
autoapi_add_toctree_entry = False


## autodoc
extensions.append("sphinx.ext.autodoc")
autodoc_typehints = "none"  # napoleon deals with these
autodoc_member_order = "groupwise"
# autodoc_undoc_members = False


## autodoc_pydantic
extensions.append("sphinxcontrib.autodoc_pydantic")
autodoc_pydantic_model_show_json = False
# autodoc_pydantic_model_undoc_members = False

# MyST
extensions.append("myst_parser")
myst_links_external_new_tab = True

## napoleon
extensions.append("sphinx.ext.napoleon")
napoleon_use_rtype = False  # put return types inline
napoleon_preprocess_types = True

## ViewCode
extensions.append("sphinx.ext.viewcode")
viewcode_line_numbers = True
