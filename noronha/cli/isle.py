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
@click.option(
    '--just-build', '-b', default=False, is_flag=True,
    help="Flag: do not start a service, just build the image"
)
@click.option(
    '--resource-profile', '--rp', 'resource_profile', help=
    """Name of a resource profile to be applied for each container. """
    """This profile should be configured in your nha.yaml file"""
)
@click.pass_context
def setup(ctx, **kwargs):
    
    """Start and configure this plugin"""
    
    CMD.run(
        API, 'setup', **kwargs,
        name=ctx.obj['ISLE_NAME']
    )


commands = [setup]
groups = [mongo, artif, router, nexus]

for grp in groups:
    
    isle.add_command(grp)
    
    for cmd in commands:
        grp.add_command(cmd)
