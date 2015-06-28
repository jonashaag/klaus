#!/bin/sh
( rm -rf tests/repos/test_repo
  mkdir -p tests/repos/test_repo
  cd tests/repos/test_repo
  git init
  echo Hello World > README
  git add README
  git commit -a -m "First commit"
)

py.test tests/ -v
