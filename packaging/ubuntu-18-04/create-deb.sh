#!/bin/sh

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TEMP_DIR="/tmp/noronha-dataops"
NORONHA_INST_FOLDER="/usr/share/noronha-dataops"

mkdir -p ${TEMP_DIR}

rm -rf ${TEMP_DIR}/*

mkdir -p ${TEMP_DIR}${NORONHA_INST_FOLDER}
cp -r ${BASEDIR}/../../* ${TEMP_DIR}${NORONHA_INST_FOLDER}/

mkdir -p ${TEMP_DIR}/DEBIAN

cp ${BASEDIR}/control ${TEMP_DIR}/DEBIAN/

cp ${BASEDIR}/preinst ${TEMP_DIR}/DEBIAN/
chmod 755 ${TEMP_DIR}/DEBIAN/preinst

cp ${BASEDIR}/postinst ${TEMP_DIR}/DEBIAN/
chmod 755 ${TEMP_DIR}/DEBIAN/postinst

dpkg-deb --build ${TEMP_DIR}

cp ${TEMP_DIR}.deb ${BASEDIR}/

rm -rf ${TEMP_DIR}
rm ${TEMP_DIR}.deb
