#!/bin/bash

examples=`python -c 'from noronha.common.constants import Package; print(Package.EXAMPLES)'`

cp -r ${examples}/iris/* .

log=`sh script.sh 2>/dev/null`

echo -e "${log}"

result=`echo -e "${log}" | tail -n 1`

label=`python -c "import json; print(json.loads('${result}').get('result'))"`

if [[ "${label}" == "setosa" ]] ; then
    exit 0
else
    exit 1
fi
