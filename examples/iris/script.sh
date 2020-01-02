#!/bin/bash

set -x
flags="--debug --pretty --skip-questions"

# define a model
nha ${flags} model new \
--name iris-clf \
--desc "Iris flower classifier" \
--model-file '{"name": "clf.pkl", "required": true, "desc": "Classifier saved as pickle"}' \
--data-file '{"name": "measures.csv"}' \
--data-file '{"name": "species.csv"}'

# record a dataset
nha ${flags} ds new \
--name iris-data-v0 \
--model iris-clf \
--details '{"extraction_date": "2019-04-01"}' \
--path ./datasets/

# create your project
nha ${flags} proj new \
--name botanics \
--desc "An experiment in the field of botanics" \
--git-repo 'https://my_git_server/botanics' \
--home-dir '.' \
--model iris-clf

# build your project # now it's "dockerized" :)
nha ${flags} proj build \
--from-here

# note that a docker image has been created for you
docker images noronha/*botanics*

# and it's also versioned in noronha's database
nha ${flags} bvers list

# Run a Jupyter Notebook for editing and testing your code:
# nha ${flags} note --edit --dataset iris-clf:iris-data-v0
#
# The Jupyter IDE is available at http://localhost:30088
# All packages listed in requirements.txt can be found in the default Python environment
#
# The dataset iris-data-v0 of the model iris-clf can be accessed by the following shortcut:
# from noronha.tools.shortcuts import *
# data_path('measures.csv')  # returns '/data/iris.iris-data-v0/measures.csv'

# execute your first training # this is going to use the training notebook
nha ${flags} train new \
--name experiment-v1 \
--nb notebooks/train \
--params '{"gamma": 0.001, "kernel": "poly"}' \
--dataset iris-clf:iris-data-v0

# check out which model versions have been produced so far
nha ${flags} movers list

# deploy a model version to homologation
nha ${flags} depl new \
--name homolog \
--nb notebooks/predict \
--port 30050 \
--movers iris-clf:experiment-v1 \
--n-tasks 1 \
&& sleep 10

# test your api (direct call to the service)
curl -X POST \
--data '[1,2,3,4]' \
http://127.0.0.1:30050/predict \
&& echo

# test your api (call through model router)
curl -X POST \
-H 'Content-Type: application/JSON' \
--data '{"project": "botanics", "deploy": "homolog", "data": [1,2,3,4]}' \
http://127.0.0.1:30080 \
&& echo
