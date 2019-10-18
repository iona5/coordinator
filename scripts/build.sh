#!/bin/bash
set -ex

BUILD_DIR=$1

cd $BUILD_DIR

bash scripts/build_help.sh

pyrcc5 -o resources.py resources.qrc
rm -rf __pycache__ \
  .git* \
  scripts \
  icons \
  README.md \
  i18n/af.ts \
  i18n/coordinator_*.ts \
  i18n/coordinator.pro \
  .gitlab-ci.yml \
  .travis.yml

