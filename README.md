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
