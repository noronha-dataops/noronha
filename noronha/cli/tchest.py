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

from noronha.api.tchest import TreasureChestAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict


@click.group()
def tchest():
    
    """Manage Treasure Chests (credentials)"""


@click.command()
@click.option('--name', '-n', help="Name of the Treasure Chest")
def info(**kwargs):
    
    """Information about a Treasure Chest"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--name', '-n', help="Name of the Treasure Chest")
def rm(**kwargs):
    
    """Remove a Treasure Chest"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
def _list(_filter, expand, **kwargs):
    
    """List Treasure Chests"""
    
    CMD.run(
        API, 'lyst', **kwargs,
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Treasure Chest', expand=expand)
    )


@click.command()
@click.option('--name', '-n', help="Name of the Treasure Chest (defaults to a random name)")
@click.option('--desc', default='', help="Free text description")
@click.option('--details', help="JSON with details related to the Treasure Chest")
@click.option('--user', '-u', help="Username to be stored in the Treasure Chest")
@click.option('--pswd', '-p', help="Password to be stored in the Treasure Chest")
def new(details, **kwargs):
    
    """Record a new Treasure Chest in the framework"""
    
    CMD.run(
        API, 'new', **kwargs,
        details=assert_dict(details, allow_none=True)
    )


@click.command()
@click.option('--name', '-n', help="Name of the Treasure Chest (defaults to a random name)")
@click.option('--desc', default='', help="Free text description")
@click.option('--details', help="JSON with details related to the Treasure Chest")
@click.option('--user', '-u', help="Username to be stored in the Treasure Chest")
@click.option('--pswd', '-p', help="Password to be stored in the Treasure Chest")
def update(details, **kwargs):
    
    """Update a Treasure Chest"""
    
    CMD.run(
        API, 'update', **kwargs,
        details=assert_dict(details, allow_none=True)
    )


commands = [new, _list, rm, update, info]

for cmd in commands:
    tchest.add_command(cmd)
