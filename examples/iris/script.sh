#!/bin/bash

set -x

# define a model
nha -v model new \
--name iris-clf \
--desc "Iris flower classifier" \
--model-file '{"name": "clf.pkl", "required": true, "desc": "Classifier saved as pickle"}' \
--data-file '{"name": "measures.csv"}' \
--data-file '{"name": "species.csv"}'

# record a dataset
nha -v ds new \
--model iris-clf \
--name iris-data-v0 \
--details '{"extraction_date": "2019-04-01"}' \
--path ./datasets/

# create your project
nha -v proj new \
--name botanics \
--desc "An experiment in the field of botanics" \
--model iris-clf

# build your project # now it's "dockerized" :)
nha -d proj build

# note that a docker image has been created for you
docker images noronha/*botanics*

# and it's also versioned in noronha's database
nha -v bvers list

# run a notebook for editing and testing your code at http://localhost:30088
# nha -d note --edit

# execute your first training # this is going to use the training notebook
nha -s -d -p train new \
--name experiment-v1 \
--nb notebooks/train \
--params '{"gamma": 0.001, "kernel": "poly"}' \
--model iris-clf \
--dataset iris-data-v0

# check out which model versions have been produced so far # which one should we choose?
nha -v movers list

# deploy everything to homologation
nha -s -d -p depl new \
--name homolog \
--nb notebooks/predict \
--port 30050 \
--model iris-clf \
--movers experiment-v1 \
--n-tasks 1 \
&& sleep 10

# test your api (direct call to the service)
curl -X POST \
--data '[1,2,3,4]' \
http://127.0.0.1:30050/predict

# test your api (call through model router)
curl -X POST \
-H 'Content-Type: application/JSON' \
--data '{"project": "botanics", "deploy": "homolog", "data": [1,2,3,4]}' \
http://127.0.0.1:30080
