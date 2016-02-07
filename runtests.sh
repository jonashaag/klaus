#!/bin/sh -e
( cd tests/repos/
  rm -rf build
  for maker in scripts/*; do
    builddir="build/`basename $maker`"
    mkdir -p $builddir
    ( cd $builddir; ../../$maker )
  done
)

tests="$1"
if [ -z "$tests" ]; then
  tests="tests/"
fi

PYTHONPATH=tests py.test $tests -v
