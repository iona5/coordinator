#!/bin/bash

set +ex
if [ -z $1 ] ; then QGIS_RELEASE=$1 ; fi

docker run -d --name qgis-${QGIS_RELEASE} -e DISPLAY=:99 qgis/qgis:release-${QGIS_RELEASE}
./docker_test_setup.sh qgis-${QGIS_RELEASE}
sleep 2
docker exec -t qgis-${QGIS_RELEASE} sh -c "qgis_testrunner.sh coordinator.test.runtests_docker"
docker stop qgis-${QGIS_RELEASE}
docker rm qgis-${QGIS_RELEASE}



