#!/bin/bash

# UNDER CONSTRUCTION
# THIS EXAMPLE SHOULD USE A PRE-TRAINED NLP MODEL
# THE COMMANDS BELLOW SHOW HOW A PRE-TRAINED MODEL CAN BE USED IN A NORONHA TRAINING

set -x

# define the pre-trained model
nha -v model new \
--name bioset \
--desc "Pre-trained model for working in Biology" \
--model-file '{"name": "bioset.pkl"}' \
--data-file '{"name": "bioset.csv"}'

# publish a pre-trained model version
nha -v movers new \
--model bioset \
--name base \
--path bioset.pkl

# use it in a training of your actual model
nha -s -d -p train new \
--name experiment-v1 \
--nb notebooks/train \
--params '{"gamma": 0.001, "kernel": "poly"}' \
--model iris-clf \
--dataset iris-data-v0 \
--pretrained bioset:base
