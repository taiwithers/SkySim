## Development Installation

### Using Nix + Direnv
```bash
git clone https://github.com/taiwithers/SkySim.git
cd SkySim
direnv allow
pre-commit install
```
## Style checking
```
isort .
black .
dmypy run -- .
pytest
```

### IPython Notebooks
```bash
nbqa black <filename(s)>
nbqa isort <filename(s)> --profile=black
nbqa pylint <filename(s)> --output-format=colorized --jobs=0 --ignored-modules="astropy.units" --recursive
nbqa pyright <filename(s)> # haven't investigated pyright yet
nbqa mypy <filename(s)> # haven't investigated mypy yet
```

pyproject.toml:

[tool.isort]
profile = "black"
