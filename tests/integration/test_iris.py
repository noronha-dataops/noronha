# -*- coding: utf-8 -*-

import os
import json
import time
from shutil import copytree, rmtree
from subprocess import check_output

from noronha.api.model import ModelAPI
from noronha.api.ds import DatasetAPI
from noronha.api.proj import ProjectAPI
from noronha.api.movers import ModelVersionAPI
from noronha.api.train import TrainingAPI
from noronha.api.depl import DeploymentAPI
from noronha.api.bvers import BuildVersionAPI
from noronha.bay.captain import get_captain
from noronha.common.constants import Package


TEST_CASE = '1_iris'
DELAY = 60  # seconds
ATTEMPTS = 3

# setup
copytree(os.path.join(Package.EXAMPLES, TEST_CASE), TEST_CASE)
os.chdir(TEST_CASE)

# define a model
ModelAPI().new(
    name='iris-clf',
    desc='Iris flower classifier',
    model_files=[
        dict(
            name='clf.pkl',
            required=True,
            desc='Classifier saved as pickle'
        )
    ],
    data_files=[
        dict(
            name='measures.csv'
        ),
        dict(
            name='species.csv'
        )
    ]
)

# record a dataset
DatasetAPI().new(
    model='iris-clf',
    name='iris-data-v0',
    details=dict(
        extraction_data='2019-04-01'
    ),
    path='./datasets/'
)

# create your project
proj = ProjectAPI().new(
    name='botanics',
    desc='An experiment in the field of botanics',
    models=['iris-clf']
)

# instantiating project depending api's in current working directory
proj_api = ProjectAPI(proj)
bvers_api = BuildVersionAPI(proj)
train_api = TrainingAPI(proj)
depl_api = DeploymentAPI(proj)

# build your project # now it's "dockerized" :)
proj_api.build()

# and it's also versioned in noronha's database
bvers_api.lyst()

# execute your first training # this is going to use the training notebook
train_api.new(
    name='experiment-v1',
    notebook='notebooks/train',
    params=dict(
        gamme=0.001,
        kernel='poly'
    ),
    datasets=['iris-clf:iris-data-v0']
)

# check out which model versions have been produced so far
ModelVersionAPI().lyst()

# deploy a model version to homologation
depl_api.new(
    name='homolog',
    notebook='notebooks/predict',
    port=30050,
    movers=['iris-clf:experiment-v1'],
    tasks=1
)

node_ip = get_captain().compass.get_node()


# test your api (call through model router)
def call_router():
    return check_output([
        'curl', '-X', 'POST', '-H', 'Content-Type: application/JSON',
        '--data', json.dumps([1, 2, 3, 4]),
        'http://{}:30082/predict?project=botanics&deploy=homolog'.format(node_ip)
    ]).decode('UTF-8')


# validation
out, error = None, None

for _ in range(ATTEMPTS):
    try:
        time.sleep(DELAY)
        out = call_router()
        assert json.loads(out).get('result') == 'setosa'
    except Exception as e:
        error = e
    else:
        break
else:
    raise ValueError("Unexpected request response: {}".format(out)) from error

# resizing to 2 tasks
depl_api.new(
    name='homolog',
    notebook='notebooks/predict',
    port=30050,
    movers=['iris-clf:experiment-v1'],
    tasks=2
)

# deployment removal
depl_api.rm(
    name='homolog'
)

# clean
os.chdir('..')
rmtree(TEST_CASE)
