#!/bin/bash
set -e

if [ -z $SRC_DIR ] ; then
	SRC_DIR=.
else
	SRC_DIR=$1
fi


if [ -z $2 ] ; then
	BUILD_DIR=$(mktemp -d -t coordinator-build-XXXXXXXX)
else
	BUILD_DIR=$2
fi

GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null)


echo "Building coordinator in ${BUILD_DIR}"

# copy sources to build dir
cp -a ${SRC_DIR}/* ${BUILD_DIR}/

# build resources
bash scripts/build_help.sh ${BUILD_DIR} ${GIT_COMMIT}
pyrcc5 -o ${BUILD_DIR}/resources.py  ${BUILD_DIR}/resources.qrc

# remove dev folders
rm -rf ${BUILD_DIR}/{__pycache__,.git*,scripts,icons,README.md,i18n/af.ts,i18n/coordinator_*.ts,i18n/coordinator.pro,.gitlab-ci.yml,.travis.yml}

echo -e "BUILD FINISHED\n------------------\n-> ${BUILD_DIR}\n"