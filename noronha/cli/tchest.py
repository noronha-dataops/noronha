# -*- coding: utf-8 -*-

import click

from noronha.api.tchest import TreasureChestAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.utils import assert_dict


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
