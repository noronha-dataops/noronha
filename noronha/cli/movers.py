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

from noronha.api.movers import ModelVersionAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict


@click.group()
def movers():
    
    """Model version management"""


@click.command()
@click.option('--model', '-m', required=True, help="Name of the model to which this version belongs")
@click.option('--name', '-n', help="Name of the version")
def info(**kwargs):
    
    """Information about a model version"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--model', '-m', required=True, help="Name of the model to which this version belongs")
@click.option('--name', '-n', help="Name of the version")
def rm(**kwargs):
    
    """Remove a model version and all of its files"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
@click.option('--model', help="Only versions of this model will be listed")
@click.option('--dataset', 'ds', help="Only versions trained with this dataset will be listed")
@click.option('--train', help="Only model versions produced by this training will be listed")
@click.option('--proj', help="To be used along with 'train': name of the project to which this training belongs")
def _list(_filter, expand, **kwargs):
    
    """List model versions"""
    
    CMD.run(
        API, 'lyst', **kwargs,
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Model Version', expand=expand)
    )


@click.command()
@click.option('--name', '-n', help="Name of the version (defaults to a random name)")
@click.option('--model', '-m', help="The model to which this version belongs (further info: nha model --help)")
@click.option('--details', '-d', help="JSON with details related to the model version")
@click.option(
    '--path', '-p',
    help="Path to the directory that contains the model files (default: current working directory)"
)
@click.option('--dataset', 'ds', help="Name of the dataset that trained this model version")
@click.option('--train', help="Name of the training that produced this model version")
@click.option('--proj', help="To be used along with 'train': name of the project to which this training belongs")
@click.option(
    '--pretrained', help=
    """Reference to another model version that was used as a pre-trained model for training this one. """
    """Syntax: <model_name>:<model_version>. Example: word2vec:en-us-v1"""
)
@click.option(
    '--compress', '-c', 'compressed', default=False, is_flag=True,
    help="Flag: compress all model files to a single tar.gz archive"
)
@click.option('--skip-upload', default=False, is_flag=True, help="Flag: don't upload any files, just record metadata")
@click.option('--lightweight', '--lw', 'lightweight', default=False, is_flag=True, help="Flag: use lightweight storage")
def new(details, path=None, **kwargs):
    
    """Record a new model version in the framework"""
    
    CMD.run(
        API, 'new', **kwargs,
        path=path or os.getcwd(),
        details=assert_dict(details, allow_none=True)
    )


@click.command()
@click.option('--name', '-n', required=True, help="Name of the model version you want to update")
@click.option(
    '--model', '-m', required=True,
    help="The model to which this version belongs (further info: nha model --help)"
)
@click.option('--details', '-d', help="JSON with details related to the version")
@click.option(
    '--path', '-p',
    help="Path to the directory that contains the model files (default: current working directory)"
)
@click.option('--dataset', 'ds', help="Name of the dataset that trained this model version")
@click.option('--train', help="Name of the training that produced this model version")
@click.option('--proj', help="To be used along with 'train': name of the project to which this training belongs")
@click.option(
    '--pretrained', help=
    """Reference to another model version that was used as a pre-trained model for training this one. """
    """Syntax: <model_name>:<model_version>. Example: word2vec:en-us-v1"""
)
@click.option(
    '--compress', '-c', 'compressed', default=False, is_flag=True,
    help="Flag: compress all model files to a single tar.gz archive"
)
def update(details, path=None, **kwargs):
    
    """Update a model version's details or files"""
    
    CMD.run(
        API, 'update', **kwargs,
        path=path,
        details=assert_dict(details, allow_none=True)
    )


commands = [new, _list, rm, update, info]

for cmd in commands:
    movers.add_command(cmd)
