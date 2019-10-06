# -*- coding: utf-8 -*-

import click

from noronha.api.proj import ProjectAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.utils import assert_dict


@click.group()
def proj():
    
    """Projects"""


@click.command()
@click.option('--proj', '--name', 'proj', help="Name of the project (default: current working project)")
def info(**kwargs):
    
    """Information about a project"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--proj', '--name', 'proj', default=None, help="Name of the project (default: current working project)")
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
    '--model', '-m', 'models', multiple=True,
    help="Name of an existing model. May be specified more than once (further info: nha model --help)"
)
@click.option(
    '--repo', '-r', help=
    """The project's repository. Syntaxes supported: \n"""
    """local://<path>/<to>/<local>/<directory>\n"""
    """git://<url>/<to>/<remote>/<git_repo>\n"""
    """docker://<address>/<of>/<remote>/<docker_registry>\n"""
    """(default: current working directory)"""
)
def new(**kwargs):
    
    """Host a new project in the framework"""
    
    CMD.run(API, 'new', **kwargs)


@click.command()
@click.option(
    '--proj', '--name', 'proj',
    help="Name of the project you want to update (default: current working project)"
)
@click.option('--desc', '-d', help="Free text description")
@click.option(
    '--model', '-m', 'models', multiple=True,
    help="Name of an existing model. May be specified more than once (further info: nha model --help)"
)
@click.option(
    '--repo', '-r', help=
    """The project's repository. Syntaxes supported: \n"""
    """local://<path>/<to>/<local>/<directory>\n"""
    """git://<url>/<to>/<remote>/<git_repo>\n"""
    """docker://<address>/<of>/<remote>/<docker_registry>\n"""
    """(default: current working directory)"""
)
def update(**kwargs):
    
    """Updates a projects in the database"""
    
    CMD.run(API, 'update', **kwargs)


@click.command()
@click.option('--proj', help="Name of the project (default: current working project)")
@click.option('--tag', '-t', default='latest', help="Docker tag for the image (default: latest)")
@click.option('--no-cache', 'nocache', default=False, is_flag=True,
              help="Flag: slower build, but useful when the cached layers contain outdated information")
def build(**kwargs):
    
    """Encapsulates the project in a new Docker image"""
    
    CMD.run(API, 'build', **kwargs)


commands = [info, new, build, _list, rm, update]

for cmd in commands:
    proj.add_command(cmd)
