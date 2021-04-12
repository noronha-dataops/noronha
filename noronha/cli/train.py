# -*- coding: utf-8 -*-

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

import click
import os

from noronha.api.train import TrainingAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict, kv_list_to_dict


@click.group()
def train():
    
    """Manage training executions"""


@click.command()
@click.option('--name', help="Name of the training")
@click.option(
    '--proj',
    help="Name of the project responsible for this training (default: current working project)"
)
def info(**kwargs):
    
    """Information about a training execution"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--name', help="Name of the training")
@click.option(
    '--proj',
    help="Name of the project responsible for this training (default: current working project)"
)
def rm(**kwargs):
    
    """Remove a training's metadata"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
@click.option(
    '--proj',
    help="Name of the project responsible for the trainings (default: current working project)"
)
def _list(_filter, expand, **kwargs):
    
    """List training executions"""
    
    CMD.run(
        API, 'lyst', **kwargs,
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Training Execution', expand=expand)
    )


@click.command()
@click.option('--name', help="Name of the training (defaults to a random name)")
@click.option(
    '--proj',
    help="Name of the project responsible for this training (default: current working project)"
)
@click.option(
    '--notebook', '--nb', 'notebook',
    help="Relative path, inside the project's directory structure, to the notebook that will be executed"
)
@click.option('--params', '-p', help="JSON with parameters to be injected in the notebook")
@click.option(
    '--tag', '-t', default='latest', help=
    """The training runs on top of a Docker image that belongs to the project. """
    """You may specify the image's Docker tag or let it default to 'latest'"""
)
@click.option('--env-var', '-e', 'env_vars', multiple=True, help="Environment variable in the form KEY=VALUE")
@click.option(
    '--mount', '-m', 'mounts', multiple=True, help=
    """A host path or docker volume to mount on the training container.\n"""
    """Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>\n"""
    """Example: /home/user/data:/data:rw\n"""
)
@click.option(
    '--dataset', '--ds', 'datasets',  multiple=True, help=
    """Reference to a dataset to be mounted on the training container. """
    """Syntax: <model_name>:<dataset_name>. Example: iris-clf:iris-data-v0"""
)
@click.option(
    '--pretrained', 'movers',  multiple=True, help=
    """Reference to a model version that will be used as a pre-trained model during this training. """
    """Syntax: <model_name>:<version_name>. Example: word2vec:en-us-v1"""
)
@click.option(
    '--resource-profile', '--rp', 'resource_profile', help=
    """Name of a resource profile to be applied for each container. """
    """This profile should be configured in your nha.yaml file"""
)
@click.option(
    '--target-deploy', '--td', 'target_deploy', help=
    """Name of deployment to be updated with the model that is generated in this training. """
    """This option only works when using LazyModelServing in your deployment"""
)
def new(params, env_vars, mounts, **kwargs):
    
    """Execute a new training"""
    
    CMD.run(
        API, 'new', **kwargs,
        params=assert_dict(params, allow_none=True),
        env_vars=kv_list_to_dict(env_vars),
        mounts=list(mounts)
    )


commands = [new, _list, rm, info]

for cmd in commands:
    train.add_command(cmd)
