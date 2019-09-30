#!/bin/bash

set -x

examples=`python -c 'from noronha.common.constants import Package; print(Package.EXAMPLES)'` &>/dev/null

cp -r ${examples}/iris/* .

log=`sh script.sh 2>&1`

set +x

result=`echo -e "${log}" | tail -n 1`

label=`python -c "import json; print(json.loads('${result}').get('result'))" 2>/dev/null`

if [[ "${label}" == "setosa" ]] ; then
    exit 0
else
    exit 1
fi
