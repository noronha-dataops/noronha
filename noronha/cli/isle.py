# -*- coding: utf-8 -*-

import click
from noronha.api.island import IslandAPI as API
from noronha.cli.handler import CMD


@click.group()
@click.pass_context
def isle(ctx):
    
    """Manage Islands (i.e.: dockerized plugins)"""


@click.group()
@click.pass_context
def mongo(ctx):
    
    """Database for metadata"""
    
    ctx.obj['ISLE_NAME'] = 'mongo'


@click.group()
@click.pass_context
def artif(ctx):
    
    """Binary files manager"""
    
    ctx.obj['ISLE_NAME'] = 'artif'


@click.group()
@click.pass_context
def nexus(ctx):
    
    """Binary files manager (alternative)"""
    
    ctx.obj['ISLE_NAME'] = 'nexus'


@click.group()
@click.pass_context
def router(ctx):
    
    """(Optional) Routes requests to deployments"""
    
    ctx.obj['ISLE_NAME'] = 'router'


@click.command()
@click.option(
    '--skip-build', '-s', default=False, is_flag=True,
    help="Flag: assume that the required Docker image for setting up this plugin already exists"
)
@click.pass_context
def setup(ctx, **kwargs):
    
    """Start and configure this plugin"""
    
    CMD.run(
        API, 'setup', **kwargs,
        name=ctx.obj['ISLE_NAME'],
        _proj_resolvers=None  # force project resolution skip, since MongoDB may not be running yet
    )


commands = [setup]
groups = [mongo, artif, router, nexus]

for grp in groups:
    
    isle.add_command(grp)
    
    for cmd in commands:
        grp.add_command(cmd)
