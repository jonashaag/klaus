#!/bin/sh -e
( cd tests/repos/
  rm -rf build
  for maker in scripts/*; do
    builddir="build/`basename $maker`"
    mkdir -p $builddir
    ( cd $builddir; ../../$maker )
  done
)

if [ $# -eq 0 ]; then
  args="-v tests/"
else
  args="$@"
fi

PYTHONPATH=tests py.test "$args"
