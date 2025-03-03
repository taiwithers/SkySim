## Development Installation

### Using Nix + Direnv
```bash
git clone https://github.com/taiwithers/SkySim.git
cd SkySim
direnv allow
pre-commit install
```

### Style checking
```bash
isort .
black .
dmypy run -- --package skysim
pytest # or pytest --pdb which uses ipdb
```

### Build Docs
```bash
trash docs/source/generated/*.rst
sphinx-apidoc --output-dir docs/source/generated skysim/
sphinx-build -M html docs/source docs/build/ --write-all
xdg-open docs/build/html/index.html
```


### Ignore warnings
```py
# Missing docstring
    # pylint: disable=missing-function-docstring
```
