"""Calling module for the SkySim package."""

# License: GPLv3+ (see COPYING); Copyright (C) 2025 Tai Withers

import argparse
import sys
from pathlib import Path

# skysim. is required to run file as python <file>, but not for poetry install
# TODO: check requirement for pip install
from skysim.plot import create_plot
from skysim.populate import create_image_matrix
from skysim.query import get_body_locations, get_planet_table, get_star_table
from skysim.settings import check_for_overwrite, confirm_config_file, load_from_toml
from skysim.utils import read_pyproject


def parse_args(args: list[str] | None) -> argparse.Namespace:
    """Parse command line arguments.

    Parameters
    ----------
    args : list[str] | None
        Arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    pyproject = read_pyproject()
    executable = list(pyproject["scripts"].keys())[0]
    version_string = f"{pyproject['name']} {pyproject['version']}"
    verbosity_options = {0: "silent", 1: "default", 2: "more output"}
    default_verbosity = [k for k, v in verbosity_options.items() if v == "default"][0]

    # instantiate the parser with project info
    parser = argparse.ArgumentParser(
        prog=executable,
        description=pyproject["description"],
        epilog="\n".join(
            [
                version_string,
                "Repository: " + pyproject["urls"]["repository"],
                "License: " + pyproject["license"],
            ]
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # add cli arguments/options
    parser.add_argument("config_file", help="TOML configuration file")
    parser.add_argument(
        "--debug",
        help="print full Python traceback, causes an exit code of 1, even on success",
        action="store_true",
    )
    parser.add_argument(
        "--overwrite", help="overwrite existing file(s)", action="store_true"
    )
    parser.add_argument(
        "--verbose",
        help=str(verbosity_options)[1:-1].replace("'", ""),  # remove {}, ''
        choices=verbosity_options.keys(),
        type=int,  # casts input to int before applying choices
        default=default_verbosity,
    )
    parser.add_argument(
        "--version",
        version=version_string,
        action="version",
    )

    return parser.parse_args(args)


def main(  # pylint: disable=inconsistent-return-statements
    args: list[str] | None = None,
) -> Path | None:
    """Entrypoint for the SkySim package. Calls the high-level functions from
    the other modules.

    Parameters
    ----------
    args : list[str] | None , default None
        When called via command line, this is None, and argparse captures the arguments
        directly.
        When running `main()` inside of python (e.g., with pytest), `args` holds a list
        of arguments.

    Returns
    -------
    pathlib.Path
        Path object to the created file.

    Raises
    ------
    ValueError, ConnectionError
        Re-raised from their creation inside the SkySim code if and only if
        the --debug flag is set.

    SystemExit
        Supercedes internal errors to produce a cleaner error message if the
        --debug flag is not set.
    """
    options = parse_args(args)

    try:
        config_path = confirm_config_file(options.config_file)

        image_settings, plot_settings = load_from_toml(config_path)

        overwritten_path = check_for_overwrite(plot_settings)  # type: ignore[arg-type]
        if (overwritten_path is not None) and (not options.overwrite):
            raise ValueError(
                "Running SkySim would overwrite one or more files, use the "
                "--overwrite flag or change/remove the output path to continue."
            )
        # TODO: add integration between verbose and overwrite flags
        # to print paths to be overwritten

        star_table = get_star_table(
            image_settings.observation_radec,
            image_settings.field_of_view,
            image_settings.maximum_magnitude,
            image_settings.object_colours,
        )

        body_locations = get_body_locations(
            image_settings.observation_times, image_settings.earth_location
        )
        planet_tables = get_planet_table(body_locations)

        image = create_image_matrix(
            image_settings,  # type: ignore[arg-type]
            planet_tables,
            star_table,
            options.verbose,
        )

        create_plot(plot_settings, image, options.verbose)  # type: ignore[arg-type]

    # Optionally print simple error message instead of full traceback
    except (ValueError, ConnectionError) as e:
        if options.debug:
            raise e

        sys.stderr.write(f"skysim: error: {' '.join(e.args)}")
        sys.exit(1)

    if options.debug:
        # note: returning a value means that an exit code of 1 is always returned
        # therefore --debug should not be used in pipelines
        return plot_settings.filename

    return  # type: ignore[return-value]
