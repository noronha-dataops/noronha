#!/bin/bash

# Copyright Noronha Development Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# same environment variables as in the base image's Dockerfile
export NHA_HOME=/nha
export SHARED_MODEL_DIR=${NHA_HOME}/model
export LOCAL_MODEL_DIR=/model
export SHARED_DATA_DIR=${NHA_HOME}/data
export LOCAL_DATA_DIR=/data
export LOG_DIR=/logs
export APP_HOME=/app
export CONDA_HOME=/etc/miniconda
export CONDA_VENV=py3_default


# script's arguments parsing
while [[ $# -gt 0 ]]
do
key="$1"

case ${key} in
    # path to the notebook file inside the project's structure (under APP_HOME)
    -n|--notebook-path)
    NOTEBOOK_PATH="$2"
    shift
    shift
    ;;
    # notebook parameters to be passed with papermill
    -p|--params)
    PARAMS="$2"
    shift
    shift
    ;;
    # flag: keep the notebook's output
    -d|--debug)
    DEBUG=True
    shift
    ;;
    *)   
    shift
    ;;
esac
done

DEBUG=${DEBUG:-False}
PARAMS=${PARAMS:-"{}"}

VENV_HOME="${CONDA_HOME}/envs/${CONDA_VENV}"
IPYNB_CKPT_DIR=".ipynb_checkpoints"

# retrieving the model, if a model was shared
mkdir -p ${LOCAL_MODEL_DIR}
cp -r ${SHARED_MODEL_DIR}/* ${LOCAL_MODEL_DIR}/ 2>/dev/null

# retrieving the dataset, if a dataset was shared
mkdir -p ${LOCAL_DATA_DIR}
cp -r ${SHARED_DATA_DIR}/* ${LOCAL_DATA_DIR}/ 2>/dev/null

# if no notebook path was provided, just open the notebook IDE
if [[ "${NOTEBOOK_PATH}" == "" ]] ; then
    mkdir -p ~/.jupyter
    JUPYTER_CONF=~/.jupyter/jupyter_notebook_config.py
    echo "c.NotebookApp.token = u''" > ${JUPYTER_CONF}
    echo "c.NotebookApp.password = u''" >> ${JUPYTER_CONF}
    mkdir -p ${IPYNB_CKPT_DIR}
    chmod 777 ${IPYNB_CKPT_DIR}
    ${VENV_HOME}/bin/jupyter notebook --allow-root --ip "0.0.0.0"
    rm -rf ${IPYNB_CKPT_DIR}
else
    script=${script}"import os; "
    script=${script}"from noronha.tools.notebook import NotebookRunner; "
    script=${script}"runner = NotebookRunner(debug=${DEBUG}); "
    script=${script}"output = runner(note_path='${NOTEBOOK_PATH}', params=${PARAMS}); "
    script=${script}"print(output); "

    output_log=`${VENV_HOME}/bin/python -c "${script}"`
    return_code="${output_log:-1}"
    code_pattern='^[0-9]+$'

    if ! [[ "${return_code}" =~ $code_pattern ]] ; then
        echo -e "${output_log}"
        exit 1
    else
        exit ${return_code}
    fi

fi
