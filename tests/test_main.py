"""Tests for functions in the __main__ module."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from skysim.__main__ import (
    check_for_overwrite,
    confirm_config_file,
    handle_overwrite,
    main,
    parse_cli_args,
)
from skysim.settings import load_from_toml

from .utils import config_name_to_path

# parse_cli_args


@pytest.mark.parametrize(
    "args",
    [
        ["-h"],
        ["--help"],
        ["--version"],
    ],
)
def test_parse_cli_args_exits(args: list[str]) -> None:
    """Test cases where the parser throws a successful sysexit (print message and exit).

    Parameters
    ----------
    args : list[str]
        CLI args to pass.
    """
    with pytest.raises(SystemExit) as sysexit:
        parse_cli_args(args)

    # for cases where things should go fine, check that against the exit code
    assert sysexit.value.code == 0


@pytest.mark.parametrize(
    "args,exception_string",
    [
        ([], "error: the following arguments are required"),
        (["a", "b"], "error: unrecognized arguments"),
    ],
)
def test_parse_cli_args_errors(
    capsys: pytest.CaptureFixture[str], args: list[str], exception_string: str
) -> None:
    """Test cases where the parser throws a sysexit because something went wrong
    (parsing failures).

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Pytest fixture for capturing output to stdout and stderr.
    args : list[str]
        Arguments to pass to parser.
    exception_string : str
        String that should be in the exception message.
    """

    with pytest.raises(SystemExit) as sysexit:
        parse_cli_args(args)

    # check that the correct exit code is given
    assert sysexit.value.code == 2  # usage error

    # check the error message
    exception_message = capsys.readouterr().err
    assert exception_string in exception_message


@pytest.mark.parametrize("debug", ([False, True]))
@pytest.mark.parametrize("overwrite", ([False, True]))
@pytest.mark.parametrize("verbose", ([0, 1, 2]))
def test_parse_cli_args_passes(debug: bool, overwrite: bool, verbose: int) -> None:
    """Check that argparse doesn't mangle options, and that all combinations are valid.

    Parameters
    ----------
    debug : bool
        Whether to set the --debug flag.
    overwrite : bool
        Whether to set the --overwrite flag.
    verbose : int
        What value to set the --verbose flag.
    """
    args = [f"--verbose={verbose}", "not-a-config-file"]
    if debug:
        args.append("--debug")
    if overwrite:
        args.append("--overwrite")

    parsed_args = parse_cli_args(args)

    assert parsed_args.verbose == verbose
    assert parsed_args.debug == debug
    assert parsed_args.overwrite == overwrite


# confirm_config_file


@pytest.mark.parametrize(
    "filename,error_message",
    [
        ("nonexistent.toml", "does not exist."),
        ("not_toml.txt", "does not have"),
        ("", "not a file."),  # points to the configs directory
    ],
)
def test_confirm_config_file(filename: str, error_message: str) -> None:
    """Test that the confirm_config_file function throws appropriate errors when
    the config file cannot be read.

    Parameters
    ----------
    filename : str
        Name of the file to check for (with extension).
    error_message : str
        The error message to check for.
    """
    with pytest.raises(ValueError, match=error_message):
        confirm_config_file(config_name_to_path(filename, ext=""))


# check_for_overwrite


@pytest.mark.parametrize(
    "config_name,overwrite_files",
    [("still_image", ["SkySim.png"]), ("movie", ["SkySim.mp4", "SkySimFiles/00.png"])],
)
def test_check_for_overwrite(
    mk_overwriteable: Callable[[Path], None],
    config_name: str,
    overwrite_files: list[str],
) -> None:
    """Ensure that `check_for_overwrite` correctly identifies pre-existing files.

    Parameters
    ----------
    mk_overwriteable : Callable[[Path], None]
        Fixture to create and clean up the files that `check_for_overwrite` would flag.
    config_name : str
        Name of the config file to use.
    overwrite_files : list[str]
        Names of files to create and then test for.
    """
    overwrite_filepaths = [Path(f).resolve() for f in overwrite_files]
    plot_settings = load_from_toml(config_name_to_path(config_name))[1]

    for fp in overwrite_filepaths:
        mk_overwriteable(fp)

    files_being_overwritten = check_for_overwrite(plot_settings)

    overwrite_filepaths.sort()
    files_being_overwritten.sort()

    assert overwrite_filepaths == files_being_overwritten


# handle_overwrite


@pytest.mark.parametrize(
    "config_name,overwrite_files",
    [("still_image", ["SkySim.png"]), ("movie", ["SkySim.mp4", "SkySimFiles/00.png"])],
)
def test_check_handle_overwrite(
    capsys: pytest.CaptureFixture[str],
    mk_overwriteable: Callable[[Path], None],
    config_name: str,
    overwrite_files: list[str],
) -> None:
    """Check that handle_overwrite returns the appropriate output when it finds existing
    files, and that the output is affected by the CLI flags.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Pytest fixture.
    mk_overwriteable : Callable[[Path], None]
        Fixture to create tempfiles.
    config_name : str
        Config file for setup.
    overwrite_files : list[str]
        Files for handle_overwrite to run into.
    """

    overwrite_filepaths = [Path(f).resolve() for f in overwrite_files]
    plot_settings = load_from_toml(config_name_to_path(config_name))[1]
    for fp in overwrite_filepaths:
        mk_overwriteable(fp)

    verbosity_checks = [(0, "one or more"), (1, "one or more"), (2, "the following")]

    # check that the right error message is output based on the verbosity
    for verbose_level, message in verbosity_checks:

        # overwrite enabled, check against stdout
        cli_args = [f"--verbose={verbose_level}", "--overwrite", config_name]
        handle_overwrite(plot_settings, parse_cli_args(cli_args))
        assert message in capsys.readouterr().out

        # overwrite disabled, check against error
        cli_args = [f"--verbose={verbose_level}", "--debug", config_name]
        with pytest.raises(ValueError, match=message):
            handle_overwrite(plot_settings, parse_cli_args(cli_args))


# main


def test_main_debug() -> None:
    """Check that the debug flag raises ValueErrors instead of SystemExits, and
    that the ValueError has an argument.
    """
    with pytest.raises(SystemExit) as regular_exception:
        main(["bad_config_path"])
    regular_exception_args = regular_exception.value.args[0]
    assert regular_exception_args == 1  # the system exit code

    with pytest.raises(ValueError) as debug_exception:
        main(["--debug", "bad_config_path"])
    debug_exception_args = debug_exception.value.args[0]  # string passed to ValueError

    assert len(debug_exception_args) > 1  # string should not be empty


@pytest.fixture(scope="session")
def created_imagepath(config_path: Path) -> Path:
    """Run the main SkySim command, return the saved filename, and clean up once
    the requesting function is finished.

    Parameters
    ----------
    config_path : Path
        Pytest fixture.

    Yields
    ------
    Path
        The file output by main().
    """
    result = main(["--debug", "--overwrite", str(config_path)])

    yield result

    if result.exists():
        result.unlink()


def test_image_creation(created_imagepath: Path) -> None:
    """Check that the file was actually created.

    Parameters
    ----------
    created_imagepath : Path
        Filename.
    """
    assert created_imagepath.exists()


def test_image_contents(created_imagepath: Path) -> None:
    """Check that the image contains at least 3 distinct colours. Only runs on
    images, not videos.

    Parameters
    ----------
    created_imagepath : Path
        Filename.
    """
    if created_imagepath.suffix == ".mp4":
        pytest.skip(reason="Can't run PIL-based checks on video files.")
    im = Image.open(created_imagepath)
    rgb = np.array([list(im.getdata(i)) for i in (0, 1, 2)])
    rgb = np.unique(rgb, axis=1)
    n_colours = rgb.shape[1]
    assert n_colours > 2
