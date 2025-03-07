# -----------------------------------
#  Just meta-recipes
# -----------------------------------

# list available recipes
[group('meta')]
default:
  @just --list --explain --unsorted

# generate and activate completions
[group('meta')]
complete shell="bash":
  just --completions {{shell}} > /tmp/just.completions
  source /tmp/just.completions

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

[group('docs')]
build-docs:
  trash docs/source/generated docs/build
  sphinx-build -M html docs/source docs/build/ --write-all

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
