#!/bin/bash

set -x

examples=`python -c 'from noronha.common.constants import Package; print(Package.EXAMPLES)'`

cp -r ${examples}/iris/* .

sh script.sh

exit $?
