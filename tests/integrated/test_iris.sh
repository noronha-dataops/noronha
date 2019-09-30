#!/bin/bash

set -x

examples=`python -c 'from noronha.common.constants import Package; print(Package.EXAMPLES)'`

cp -r ${examples}/iris/* .

log=`sh script.sh 2>/dev/null`

echo -e "${log}"

result=`echo -e "${log}" | tail -n 1`

expected='{"result": "setosa", "metadata": {"datetime": "2019-09-30 13:51:55", "model_version": "experiment-v1"}}'

if [[ "${result}" == "${expected}" ]] ; then
    exit 0
else
    exit 1
fi
