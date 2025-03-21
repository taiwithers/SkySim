# SkySim

See this page and the developer documentation at [taiwithers.github.io/SkySim](https://taiwithers.github.io/SkySim/)

## General Installation & Usage

1. Confirm you have the required dependencies:
    - [git](https://git-scm.com/)
    - [poetry](https://python-poetry.org/) (built with 1.8)
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
