# -*- coding: utf-8 -*-

import click
import json

from noronha.api.bvers import BuildVersionAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict


@click.group()
def bvers():
    
    """Build versions (documented Docker images)"""


@click.command()
@click.option(
    '--proj',
    help="The project to which this build version belongs (default: current working project)"
)
@click.option('--tag', help="The build version's docker tag (default: latest)")
def info(**kwargs):
    
    """Information about a build version"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option(
    '--proj',
    help="The project in which this version belongs (default: current working project)"
)
@click.option('--tag', help="The version's docker tag (default: latest)")
def rm(**kwargs):
    
    """Remove a build version"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option(
    '--proj',
    help="The project whose versions you want to list (default: current working project)"
)
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
def _list(_filter, expand, **kwargs):
    
    """List build versions"""
    
    CMD.run(
        API, 'lyst', **kwargs,
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Build Version', expand=expand)
    )


# TODO: IMPLEMENT RE-BUILD, WHICH IS GONNA BE AWESOME :D

commands = [_list, rm, info]

for cmd in commands:
    bvers.add_command(cmd)
