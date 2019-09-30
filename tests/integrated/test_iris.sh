#!/bin/bash

delay=20

examples=`python -c 'from noronha.common.constants import Package; print(Package.EXAMPLES)'` &>/dev/null
cp -r ${examples}/iris/* .

echo -e "TEST LOGS:"
set -x
sh script.sh
set +x

echo "Waiting ${delay} seconds..."
sleep ${delay}

output=$(
    curl -s -w "%{http_code}" -X POST \
    -H 'Content-Type: application/JSON' \
    --data '{"project": "botanics", "deploy": "homolog", "data": [1,2,3,4]}' \
    http://127.0.0.1:30080 2>/dev/null
)

response=${output::-5}
code=${output: -3:4}

echo -e "RESPONSE TEXT: ${response}"
echo -e "RESPONSE CODE: ${code}"

if [[ "${code}" != "200" ]] ; then
    exit 1
fi

label=`python -c "import json; print(json.loads('${response}').get('result'))"`
echo -e "LABEL: ${label}"

if [[ "${label}" != "setosa" ]] ; then
    exit 1
fi
