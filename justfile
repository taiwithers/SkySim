# -----------------------------------
#  Just meta-recipes
# -----------------------------------

# list available recipes
[group('meta')]
default:
  @just --list --explain --unsorted


# -----------------------------------
#  pytest
# -----------------------------------
pytest-flags-fast := "--testmon --exitfirst --failed-first --new-first"
pytest-flags-interactive := "--pdb --reruns=0"

# run (needed) tests with testmon
[group('pytest')]
qtest :
  pytest {{pytest-flags-fast}}

# run pytest with debugging enabled
[group('pytest')]
itest:
  pytest {{pytest-flags-fast}}

# combine qtest and itest
[group('pytest')]
qitest:
  pytest {{pytest-flags-fast}} {{pytest-flags-interactive}}

# -----------------------------------
#  Docs
# -----------------------------------

# trash generated docs and rebuild
[group('docs')]
build-docs sphinx-build-args="":
  # leading hyphen means recipe continues even if this line fails
  -trash-put docs/source/generated docs/build
  sphinx-build -M html docs/source docs/build/ --write-all {{sphinx-build-args}}

# re-create embedded SkySim outputs and build docs
[group('docs')]
full-build-docs:
  -mkdir --parents docs/source/_static/examples
  skysim --verbose=2 examples/still_image.toml && mv SkySim.png docs/source/_static/examples/still_image.png
  skysim --verbose=2 examples/movie.toml && mv SkySim.mp4 docs/source/_static/examples/movie.mp4
  just build-docs --fail-on-warning
  rm docs/source/_static/examples/still_image.png
  rm docs/source/_static/examples/movie.mp4

# xdg-open on index.html
[group('docs')]
open-docs:
  xdg-open docs/build/html/index.html

# -----------------------------------
#  Other
# -----------------------------------

# run pre-commit on all files
validate: todo
  pre-commit run --hook-stage="manual" --all-files


# poetry add <package> to <group (optional)>
add package group="main":
  poetry add --group={{group}} {{package}}

# use pylint to locate TODO comments
todo:
  pylint . --disable=all --enable=fixme --score=false --exit-zero

# run a python file with ipdb enabled
debug filename:
  ipdb3 -c continue {{filename}}

update:
  nix flake update
  poetry update
  pre-commit autoupdate # DOWNGRADE POETRY AND POETRY-EXPORT
