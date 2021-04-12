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
import json

from noronha.api.model import ModelAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict


MODEL_FILE_EXAMPLE = dict(
    name="categories.pkl",
    desc="Pickle with DataFrame for looking up prediction labels",
    required=True,
    max_mb=64
)

DATA_FILE_EXAMPLE = dict(
    name="intents.csv",
    desc="CSV file with examples for each user intent",
    required=True,
    max_mb=128
)


@click.group()
def model():
    
    """Model management"""


@click.command()
@click.option('--name', help="Name of the model")
def info(**kwargs):
    
    """Information about a model"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--name', '-n', required=True, help="Name of the model")
def rm(**kwargs):
    
    """Remove a model along with all of it's versions and datasets"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
def _list(_filter, expand):
    
    """List model records"""
    
    CMD.run(
        API, 'lyst',
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Model Record', expand=expand)
    )


@click.command()
@click.option('--name', '-n', required=True, help="Name of the model")
@click.option('--desc', '-d', default='', help="Free text description")
@click.option(
    '--model-file', 'model_files', multiple=True,
    help="""JSON describing a file that is used for saving/loading this model. """
         """Example: {}""".format(json.dumps(MODEL_FILE_EXAMPLE))
)
@click.option(
    '--data-file', 'data_files', multiple=True,
    help="""JSON describing a file that is used for training this model. """
         """Example: {}""".format(json.dumps(DATA_FILE_EXAMPLE))
)
def new(model_files, data_files, **kwargs):
    
    """Record a new model in the database"""
    
    CMD.run(
        API, 'new', **kwargs,
        model_files=[assert_dict(f) for f in model_files],
        data_files=[assert_dict(f) for f in data_files]
    )


@click.command()
@click.option('--name', '-n', required=True, help="Name of the model you want to update")
@click.option('--desc', '-d', default='', help="Free text description")
@click.option(
    '--model-file', 'model_files', multiple=True,
    help="""JSON describing a file that is used for saving/loading this model. """
         """Example: {}""".format(json.dumps(MODEL_FILE_EXAMPLE))
)
@click.option(
    '--data-file', 'data_files', multiple=True,
    help="""JSON describing a file that is used for training this model. """
         """Example: {}""".format(json.dumps(DATA_FILE_EXAMPLE))
)
@click.option('--no-model-files', default=False, is_flag=True, help="Flag: disable the tracking of model files")
@click.option('--no-ds-files', default=False, is_flag=True, help="Flag: disable the tracking of dataset files")
def update(model_files, data_files, no_model_files: bool = False, no_ds_files: bool = False, **kwargs):
    
    """Update a model record"""
    
    CMD.run(
        API, 'update', **kwargs,
        model_files=[] if no_model_files else [assert_dict(f) for f in model_files] or None,
        data_files=[] if no_ds_files else [assert_dict(f) for f in data_files] or None
    )


commands = [new, _list, rm, update, info]

for cmd in commands:
    model.add_command(cmd)
