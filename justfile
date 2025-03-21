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

# run (needed) tests with testmon
[group('pytest')]
qtest:
  pytest --testmon --exitfirst

# run pytest with debugging enabled
[group('pytest')]
itest:
  pytest --pdb

# combine qtest and itest
[group('pytest')]
qitest:
  pytest --pdb --testmon --exitfirst

# -----------------------------------
#  Docs
# -----------------------------------

# trash generated docs and rebuild
[group('docs')]
build-docs sphinx-build-args="":
  # TODO: add fast parameter which skips skysim calls
  # leading hyphen means recipe continues even if this line fails
  -trash-put docs/source/generated docs/build
  sphinx-build -M html docs/source docs/build/ --write-all {{sphinx-build-args}}

# re-create embedded SkySim outputs and build docs
[group('docs')]
full-build-docs:
  -mkdir --parents docs/source/_static/examples
  skysim examples/still_image.toml && mv SkySim.png docs/source/_static/examples/still_image.png
  skysim examples/movie.toml && mv SkySim.mp4 docs/source/_static/examples/movie.mp4
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
validate:
  pre-commit run --hook-stage="manual" --all-files && just todo


# poetry add <package> to <group (optional)>
add package group="main":
  poetry add --group={{group}} {{package}}

# use pylint to locate TODO comments
todo:
  pylint . --disable=all --enable=fixme --score=false --exit-zero

# run a python file with ipdb enabled
debug filename:
  ipdb3 -c continue {{filename}}
