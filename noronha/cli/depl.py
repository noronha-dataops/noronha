# -*- coding: utf-8 -*-

import click
import os

from noronha.api.depl import DeploymentAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.utils import assert_dict, kv_list_to_dict


@click.group()
def depl():
    
    """Manage deployments"""


@click.command()
@click.option('--name', help="Name of the deployment")
@click.option(
    '--proj',
    help="Name of the project responsible for this deployment (default: current working project)"
)
def info(**kwargs):
    
    """Information about a deployment"""
    
    CMD.run(API, 'info', **kwargs)


@click.command()
@click.option('--name', help="Name of the deployment")
@click.option(
    '--proj',
    help="Name of the project responsible for this deployment (default: current working project)"
)
def rm(**kwargs):
    
    """Remove a deployment"""
    
    CMD.run(API, 'rm', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', help="Query in MongoDB's JSON syntax")
@click.option('--expand', '-e', default=False, is_flag=True, help="Flag: expand each record's fields")
@click.option(
    '--proj',
    help="Name of the project responsible for this deployment (default: current working project)"
)
def _list(_filter, expand, **kwargs):
    
    """List deployments"""
    
    CMD.run(
        API, 'lyst', **kwargs,
        _filter=assert_dict(_filter, allow_none=True),
        _response_callback=ListingCallback(obj_title='Deployment', obj_attr='name', expand=expand)
    )


@click.command()
@click.option('--name', help="Name of the deployment (defaults to a random name)")
@click.option(
    '--proj',
    help="Name of the project responsible for this deployment (default: current working project)"
)
@click.option(
    '--notebook', '--nb', 'notebook',
    help="Relative path, inside the project's directory structure, to the notebook that will be executed"
)
@click.option('--params', '-p', help="JSON with parameters to be injected in the notebook")
@click.option('--tag', '-t', default='latest',
              help="""Each deployment task runs on top of a Docker image that belongs to the project. """
                   """You may specify the image's Docker tag or let it default to "latest\"""")
@click.option('--n-tasks', '-n', default=1, help="Number of tasks (containers) for deployment replication (default: 1)")
@click.option('--port', '-p', help="Host port to be routed to each container's inference service")
@click.option('--env-var', '-e', 'env_vars', multiple=True, help="Environment variable in the form KEY=VALUE")
@click.option('--mount', '-m', 'mounts', multiple=True,
              help="""A host path or docker volume to mount on each deployment container.\n"""
                   """Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>\n"""
                   """Example: /home/user/data:/data:rw\n""")
@click.option('--movers', '--mv', 'movers', help="Name of a model version to be mounted on each deployment container")
@click.option('--model', help="To be used along with 'movers': name of the model to which the model version belongs")
def new(params, env_vars, mounts, port: int, n_tasks: int = 1, **kwargs):
    
    """Setup a deployment"""
    
    CMD.run(
        API, 'new', **kwargs,
        params=assert_dict(params, allow_none=True),
        env_vars=kv_list_to_dict(env_vars),
        mounts=list(mounts),
        port=None if port is None else int(port),
        tasks=int(n_tasks)
    )


commands = [new, _list, rm, info]

for cmd in commands:
    depl.add_command(cmd)
