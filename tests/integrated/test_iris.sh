#!/bin/bash

examples=`python -c 'from noronha.common.constants import Package; print(Package.EXAMPLES)'` &>/dev/null

cp -r ${examples}/iris/* .

log=`set -x && sh script.sh 2>&1`

echo -e "TEST LOGS:\n${log}"

result=`echo -e "${log}" | tail -n 1`

label=`python -c "import json; print(json.loads('${result}').get('result'))"`

if [[ "${label}" == "setosa" ]] ; then
    exit 0
else
    exit 1
fi
