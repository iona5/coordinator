#!/bin/bash

set -x
if [ -z $1 ] ; then 
	QGIS_RELEASE=3_10
else
	QGIS_RELEASE=$1
fi

DOCKER_TAG=release-${QGIS_RELEASE}

# -- 3.8 does not have "release-*" dockerfiles so we need to track that manually :(
#if [ ${QGIS_RELEASE} = 3_8 ]; then DOCKER_TAG=final-3_8_3 ; fi

docker run -d --rm --name qgis-${QGIS_RELEASE} -e DISPLAY=:99 qgis/qgis:${DOCKER_TAG}
./docker_test_setup.sh qgis-${QGIS_RELEASE}
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

