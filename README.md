# SkySim

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
