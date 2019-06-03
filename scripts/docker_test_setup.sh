#!/bin/bash

set -e
set -x

CONTAINER=$1

# display version:
docker exec ${CONTAINER} sh -c "qgis --help 2>&1 | head -n 1"

docker exec ${CONTAINER} sh -c "mkdir -p /tests_directory"
docker cp coordinator ${CONTAINER}:/tests_directory/coordinator
docker exec ${CONTAINER} sh -c "qgis_setup.sh coordinator"
