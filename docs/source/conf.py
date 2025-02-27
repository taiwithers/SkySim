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

extensions = [
    "myst_parser",  # markdown parser
    "sphinx.ext.autodoc",  # import from docstrings
    "sphinx.ext.napoleon",  # use numpy-style docstrings
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = []

viewcode_line_numbers = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
