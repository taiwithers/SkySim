# Developer Documentation

## Installation

See <project:usage.md#development-installation>.

## Testing

SkySim testing is perfomed with
[pytest](https://docs.pytest.org/en/stable/index.html), and the
[pyproject.toml](https://github.com/taiwithers/SkySim/blob/main/pyproject.toml) has been set up such that you need only run `pytest` from the
SkySim folder to run all tests with appropriate settings.
Some additional testing setups are included in the [justfile](https://github.com/taiwithers/SkySim/blob/main/justfile).

Tests are located in
the [tests directory](https://github.com/taiwithers/SkySim/tree/main/tests)
and organized by module.
The [configs subdirectory](https://github.com/taiwithers/SkySim/tree/main/tests/configs) contains various configuration files used as samples
for executing tests.
Within this folder, the `still_image.toml` and `movie.toml` files are the only
entries expected to pass all tests, and are symlinks to the identically named
entries in [examples](https://github.com/taiwithers/SkySim/tree/main/examples).

## Building the Documentation

Documentation is generated with [Sphinx](https://www.sphinx-doc.org/) and can be built locally using either the `build-docs` or
`full-build-docs` just recipes.

`full-build-docs` runs SkySim against the example configurations such that the
results can be embedded in the output. This is used for building the live
documentation (via Github actions) but is slower than purely evaluating the
Python docstrings and markdown files.
As such, for fast iteration on documentation, the `build-docs` recipe is
recommended, and one can simply disregard the "image file not readable" warning about non-existent files.
Note that this warning only appears for *images* as Sphinx does not have the
ability to directly embed videos, which are instead embedded with raw HTML directives.

Additionally, both recipes attempt to delete all generated documentation before starting (using [trash-cli](https://github.com/andreafrancia/trash-cli)) in order to avoid any
contamination.
Therefore during the build, the HTML output will be inaccessible, and no files
should be stored in the `docs/source/generated` or `docs/build` directories.
