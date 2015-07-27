#!/bin/sh -e
( cd tests/repos/
  rm -rf build
  for maker in scripts/*; do
    builddir="build/`basename $maker`"
    mkdir -p $builddir
    ( cd $builddir; ../../$maker )
  done
)

py.test tests/ -v
