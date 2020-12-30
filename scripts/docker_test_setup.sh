#!/bin/bash

set -e
set -x

CONTAINER=$1

if [ -z $2 ] ; then
	COORDINATOR_DIR=.
else
	COORDINATOR_DIR=$2
fi

# display version:
docker exec ${CONTAINER} sh -c "qgis --version 2>&1 | head -n 1"

docker exec ${CONTAINER} sh -c "mkdir -p /tests_directory"
docker cp ${COORDINATOR_DIR} ${CONTAINER}:/tests_directory/coordinator
docker exec ${CONTAINER} sh -c "qgis_setup.sh coordinator"
