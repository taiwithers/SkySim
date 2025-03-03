# list available recipes
default:
  @just --list --explain --unsorted

# run pre-commit on all files
validate:
  pre-commit run --hook-stage="manual" --all-files

build-docs:
  sphinx-apidoc --output-dir docs/source/generated skysim/
  sphinx-build -M html docs/source docs/build/ --write-all

open-docs:
  xdg-open docs/build/html/index.html

# poetry add <package> to <group (optional)>
add package group="main":
  poetry add --group={{group}} {{package}}

# run (needed) tests with testmon
qtest:
  pytest --testmon

# run pytest with debugging enabled
itest:
  pytest --pdb

# use pylint to locate TODO comments
todo:
  pylint . --disable=all --enable=fixme --score=false --exit-zero

# generate and activate completions
complete shell="bash":
  just --completions {{shell}} > /tmp/just.completions
  source /tmp/just.completions
