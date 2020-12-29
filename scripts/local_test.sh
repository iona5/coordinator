#!/bin/bash

set -ex

if [ -z $1 ] ; then 
	QGIS_RELEASE=3_10
else 
	QGIS_RELEASE=$1
fi

DOCKER_TAG=release-${QGIS_RELEASE}
CONTAINER=qgis-${QGIS_RELEASE}


docker run -d --rm --name qgis-${QGIS_RELEASE} -e DISPLAY=:99 qgis/qgis:${DOCKER_TAG}
# display version:
docker exec ${CONTAINER} sh -c "qgis --version 2>&1 | head -n 1"

docker exec ${CONTAINER} sh -c "mkdir -p /tests_directory"
docker cp ../coordinator ${CONTAINER}:/tests_directory/coordinator
docker exec ${CONTAINER} sh -c "qgis_setup.sh coordinator"

if [ ${QGIS_RELEASE} = "3_16" ] ; then
	# the QGIS 3.16 docker image has some missing packages, install these here:
	docker exec -t ${CONTAINER} sh -c "apt install --assume-yes python3-pyqt5.qtwebkit python3-pexpect expect >/dev/null" 
fi

sleep 2

#docker exec -it ${CONTAINER} /bin/bash

set +e
docker exec -t ${CONTAINER} sh -c "qgis_testrunner.sh coordinator.test.run_all"
RESULT=$?
set -e

docker stop ${CONTAINER}

if [ ${RESULT} = 0 ]; then
	echo " ----------- ALL TESTS PASSED ---------------- "
else
	echo " !!!!!!!!!! SOME TESTS FAILED !!!!!!!!!!!!!!!! "
fi

exit ${RESULT}