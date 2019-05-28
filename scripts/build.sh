#!/bin/bash
set -ex

BUILD_DIR=$1

cd $BUILD_DIR

pyrcc5 -o resources.py resources.qrc
rm -rfv __pycache__ \
  .git* \
  scripts \
  README.md \
  images \
  i18n/af.ts \
  i18n/coordinator_de.ts \
  i18n/coordinator.pro
