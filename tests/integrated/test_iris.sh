#!/bin/bash

purge(){
  nha -q depl rm --name homolog --proj botanics
  nha -q proj rm --name botanics
  nha -q model rm --name iris-clf
}

purge

cp -r ${NHA_EXAMPLES}/iris/* .

sh script.sh

purge
