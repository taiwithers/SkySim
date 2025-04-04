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
from skysim.settings import (
    PlotSettings,
    load_from_toml,
)
from skysim.utils import get_tempfile_path, read_pyproject

# Methods


## Top-Level Methods


def main(  # pylint: disable=inconsistent-return-statements
    args: list[str] | None = None,
) -> Path | None:
    """Entrypoint for the SkySim package.

    Calls the following functions directly:

    - :doc:`main`
        - `parse_args`
        - `confirm_config_file`
        - `handle_overwrite`
    - :doc:`settings`
        - `~skysim.settings.load_from_toml`
    - :doc:`query`
        - `~skysim.query.get_star_table`
        - `~skysim.query.get_body_locations`
        - `~skysim.query.get_planet_table`
    - :doc:`populate`
        - `~skysim.populate.create_image_matrix`
    - :doc:`plot`
        - `~skysim.plot.create_plot`

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
        Path object to the created file. Returned if `--debug` flag is set.
    None
        Returned if `--debug` flag is unset.

    Raises
    ------
    ValueError, ConnectionError
        Re-raised from their creation inside the SkySim code if and only if
        the --debug flag is set.

    SystemExit
        Supercedes internal errors to produce a cleaner error message if the
        --debug flag is not set.
    """

    options = parse_cli_args(args)
    try:
        config_path = confirm_config_file(options.config_file)

        image_settings, plot_settings = load_from_toml(config_path)

        handle_overwrite(plot_settings, options)

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

        sys.stderr.write(f"error: {' '.join(e.args)}")
        sys.exit(1)

    if options.debug:
        # note: returning a value means that an exit code of 1 is always returned
        # therefore --debug should not be used in pipelines
        return plot_settings.filename

    return  # type: ignore[return-value]


## Helper Methods


def parse_cli_args(args: list[str] | None) -> argparse.Namespace:
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


def confirm_config_file(input_config_path: str) -> Path:
    """Pre-validate the existence of a config file.

    Parameters
    ----------
    input_config_path : str
        Argument passed on command line.

    Returns
    -------
    pathlib.Path
        Given config file path (if any).

    Raises
    ------
    ValueError
        Raised if
        - Path given does not exist.
        - Path leads to a non-file object.
        - Path does not have a ".toml" extension.
    """

    config_path = Path(input_config_path).resolve()

    if not config_path.exists():
        raise ValueError(f"{config_path} does not exist.")
    if not config_path.is_file():
        raise ValueError(f"{config_path} is not a file.")
    if config_path.suffix != ".toml":
        raise ValueError(f"{config_path} does not have a '.toml' extension.")

    return config_path


def handle_overwrite(plot_settings: PlotSettings, options: argparse.Namespace) -> None:
    """Check if files will be overwritten and take action based on cli flags (--verbose
    and --overwrite).

    Parameters
    ----------
    plot_settings : PlotSettings
        Plotting configuration, passed to `check_for_overwrite`.
    options : argparse.Namespace
        Parsed CLI options.

    Raises
    ------
    ValueError
        Raised if an overwrite would happen but the --overwrite flag was not passed.
    """
    overwritten_paths = check_for_overwrite(plot_settings)

    # noop if no overwrites
    if len(overwritten_paths) == 0:
        return

    # if there's mutiple files, start the printout on a new line
    if len(overwritten_paths) > 1:
        overwritten_paths.insert(0, "")

    # set the printout based on verbosity
    if options.verbose > 1:
        paths_string = "\n".join([str(p) for p in overwritten_paths])
        paths_message = f"the following files: {paths_string}."
    else:
        paths_message = "one or more files."

    # display message or error based on use of --overwrite
    if options.overwrite:
        print(f"Overwriting {paths_message}")
    else:
        raise ValueError(
            f"Running SkySim would overwrite {paths_message}\nUse the --overwrite flag"
            " or change/remove the output path to continue."
        )


### Secondary Helpers


def check_for_overwrite(plot_settings: PlotSettings) -> list[Path]:
    """Check if SkySim will overwrite any existing files.

    Parameters
    ----------
    plot_settings : PlotSettings
        Configuration.

    Returns
    -------
    pathlib.Path
        Returns a list of paths that will be overwritten.
    """
    overwrites = []

    if plot_settings.filename.exists():
        overwrites.append(plot_settings.filename)

    if plot_settings.frames > 1:
        for i in range(plot_settings.frames):
            tempfile_path = get_tempfile_path(plot_settings, i)
            if tempfile_path.exists():
                overwrites.append(tempfile_path)

    return overwrites
