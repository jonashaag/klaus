#!/bin/bash -eux
( cd tests/repos/
  rm -rf build
  for maker in scripts/*; do
    builddir="build/`basename $maker`"
    mkdir -p $builddir
    ( cd $builddir; ../../$maker )
  done
)

export PYTHONPATH=tests:${PYTHONPATH}
if [ $# -eq 0 ]; then
  pytest -v tests
else
  pytest "$@"
fi
