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

from noronha.api.proj import ProjectAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict


@click.group()
def proj():
    
    """Projects"""


@click.command()
@click.option('--name', '-n', 'proj', help="Name of the project (default: current working project)")
def info(**kwargs):
    
    """Information about a project"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--name', '-n', 'proj', default=None, help="Name of the project (default: current working project)")
def rm(**kwargs):
    
    """Remove a project and everything related to it"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
def _list(_filter, expand, **kwargs):
    
    """List hosted projects"""
    
    CMD.run(
        API, 'lyst', **kwargs,
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Project', expand=expand)
    )


@click.command()
@click.option('--name', '-n', required=True, help="Name of the project")
@click.option('--desc', '-d', default='', help="Free text description")
@click.option(
    '--model', '-m', 'models', multiple=True, help=
    """Name of an existing model. May be specified more than once """
    """(further info: nha model --help)"""
)
@click.option(
    '--home-dir', help=
    """Local directory where the project is hosted. """
    """Example: /path/to/proj """
)
@click.option(
    '--git-repo', help=
    """The project's remote Git repository. """
    """Example: https://<git_server>/<proj_repo>"""
)
@click.option(
    '--docker-repo', help=
    """The project's remote Docker repository. """
    """Example: <docker_registry>/<proj_image>"""
)
def new(**kwargs):
    
    """Host a new project in the framework"""
    
    CMD.run(API, 'new', **kwargs)


@click.command()
@click.option(
    '--name', '-n', 'proj',
    help="Name of the project you want to update (default: current working project)"
)
@click.option('--desc', '-d', default='', help="Free text description")
@click.option(
    '--model', '-m', 'models', multiple=True, help=
    """Name of an existing model. May be specified more than once """
    """(further info: nha model --help)"""
)
@click.option(
    '--home-dir', help=
    """Local directory where the project is hosted. """
    """Example: /path/to/proj """
)
@click.option(
    '--git-repo', help=
    """The project's remote Git repository. """
    """Example: https://<git_server>/<proj_repo>"""
)
@click.option(
    '--docker-repo', help=
    """The project's remote Docker repository. """
    """Example: <docker_registry>/<proj_image>"""
)
def update(**kwargs):
    
    """Updates a projects in the database"""
    
    CMD.run(API, 'update', **kwargs)


@click.command()
@click.option('--name', '-n', 'proj', help="Name of the project (default: current working project)")
@click.option('--tag', '-t', default='latest', help="Docker tag for the image (default: latest)")
@click.option(
    '--no-cache', 'nocache', default=False, is_flag=True, help=
    "Flag: slower build, but useful when the cached layers contain outdated information"
)
@click.option(
    '--from-here', default=False, is_flag=True, help=
    "Flag: build from current working directory (default option)."
)
@click.option(
    '--from-home', default=False, is_flag=True, help=
    "Flag: build from project's home directory."
)
@click.option(
    '--from-git', default=False, is_flag=True, help=
    "Flag: build from project's Git repository (master branch)."
)
@click.option(
    '--pre-built', default=False, is_flag=True, help=
    "Flag: don't build, just pull and tag a pre-built image from project's Docker repository."
)
def build(**kwargs):
    
    """Encapsulates the project in a new Docker image"""
    
    CMD.run(API, 'build', **kwargs)


commands = [info, new, build, _list, rm, update]

for cmd in commands:
    proj.add_command(cmd)
