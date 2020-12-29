#!/bin/bash

set -x
if [ -z $1 ] ; then 
	QGIS_RELEASE=3_10
else
	QGIS_RELEASE=$1
fi

DOCKER_TAG=release-${QGIS_RELEASE}

docker run -d --rm --name qgis-${QGIS_RELEASE} -e DISPLAY=:99 qgis/qgis:${DOCKER_TAG}
./docker_test_setup.sh qgis-${QGIS_RELEASE}
if [ ${QGIS_RELEASE} = "3_16" ] ; then
	# the QGIS 3.16 docker image has some missing packages, install these here:
	docker exec -t qgis-${QGIS_RELEASE} sh -c "apt install --assume-yes python3-pyqt5.qtwebkit python3-pexpect expect >/dev/null" 
fi
sleep 2
docker exec -t qgis-${QGIS_RELEASE} sh -c "qgis_testrunner.sh coordinator.test.run_all"
RESULT=$?
docker stop qgis-${QGIS_RELEASE}

if [ ${RESULT} = 0 ]; then
	echo " ----------- ALL TESTS PASSED ---------------- "
else
	echo " !!!!!!!!!! SOME TESTS FAILED !!!!!!!!!!!!!!!! "
fi

exit ${RESULT}

