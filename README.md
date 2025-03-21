# SkySim

See this page and the developer documentation at [taiwithers.github.io/SkySim](https://taiwithers.github.io/SkySim/)

## General Installation & Usage

### Using pip

1. Confirm you have the required dependencies:
    - [Git](https://git-scm.com/)
    - [pip](https://pip.pypa.io/en/stable/)
    - [ffmpeg](https://ffmpeg.org/)
    - libstdc++.so.6 (libstdc++6)
    - libz.so.1 (zlib)
2. Install the package with pip: `pip install git+
   https://github.com/taiwithers/SkySim.git`
3. Create a configuration TOML file (see the [examples directory](https://github.com/taiwithers/SkySim/tree/main/examples)).
4. Run `skysim <path to your config.toml>`

### Using Poetry

1. Confirm you have the required dependencies:
    - [Git](https://git-scm.com/)
    - [Poetry](https://python-poetry.org/) (SkySim is built with version 1.8)
    - [ffmpeg](https://ffmpeg.org/)
    - libstdc++.so.6 (libstdc++6)
    - libz.so.1 (zlib)
2. Clone and enter the git repo: `git clone
   https://github.com/taiwithers/SkySim.git && cd SkySim` (disregard the
   warning from direnv if it appears).
3. Install the script and its dependencies with `poetry install --only main`.
4. Create a configuration TOML file (see the [examples directory](https://github.com/taiwithers/SkySim/tree/main/examples)).
5. Run `poetry run skysim <path to your config.toml>`

## Development Installation (Using Nix + Direnv)

SkySim is developed using [Nix](https://nixos.org/download/) as a general package manager to control the
development environment, and [direnv](https://direnv.net/) to activate that environment automatically.
If you'd prefer to manage your development environment manually, consult the
[flake.nix](flake.nix) for a list of dependencies, and [.envrc](/.envrc) for the
environment activation scripts.

```bash
git clone https://github.com/taiwithers/SkySim.git
cd SkySim
direnv allow # let direnv use the .envrc file
poetry install # install python and dependencies
direnv reload # set up and activate the environment
pre-commit install # install pre-commit checks
source $JCOMP_PATH # add completions for `just` commands
just # list the `just` commands and their usage
```

```bash
# copy-paste version
git clone https://github.com/taiwithers/SkySim.git && cd SkySim && direnv allow
poetry install && direnv reload && pre-commit install && source $JCOMP_PATH
```
