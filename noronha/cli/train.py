# -*- coding: utf-8 -*-

import click
import os

from noronha.api.train import TrainingAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.utils import assert_dict, kv_list_to_dict


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
        _response_callback=ListingCallback(obj_title='Training Execution', obj_attr='name', expand=expand)
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
@click.option('--tag', '-t', default='latest',
              help="""The training runs on top of a Docker image that belongs to the project. """
                   """You may specify the image's Docker tag or let it default to "latest\"""")
@click.option('--env-var', '-e', 'env_vars', multiple=True, help="Environment variable in the form KEY=VALUE")
@click.option('--mount', '-m', 'mounts', multiple=True,
              help="""A host path or docker volume to mount on the training container.\n"""
                   """Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>\n"""
                   """Example: /home/user/data:/data:rw\n""")
@click.option('--dataset', 'ds', help="Name of a dataset to be mounted on the training container")
@click.option('--model', help="To be used along with 'dataset': name of the model to which the dataset belongs")
@click.option(
    '--pretrained', help=
    """Reference to a model version that may be used as a pre-trained model during this training. """
    """Syntax: <model_name>:<model_version>. Example: word2vec:en-us-v1"""
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
