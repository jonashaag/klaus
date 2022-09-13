#!/bin/bash -eux
( cd tests/repos/
  rm -rf build
  for maker in scripts/*; do
    builddir="build/`basename $maker`"
    mkdir -p $builddir
    ( cd $builddir; ../../$maker )
  done
)

if [ $# -eq 0 ]; then
  python -m pytest -v tests
else
  python -m pytest "$@"
fi
