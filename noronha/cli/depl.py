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

from noronha.api.depl import DeploymentAPI as API
from noronha.cli.callback import ListingCallback
from noronha.cli.handler import CMD
from noronha.common.parser import assert_dict, kv_list_to_dict


@click.group()
def depl():
    
    """Manage deployments"""


@click.command()
@click.option('--name', '-n', help="Name of the deployment")
@click.option(
    '--proj',
    help="Name of the project responsible for this deployment (default: current working project)"
)
def info(**kwargs):
    
    """Information about a deployment"""
    
    def callback(x):
        avail = x.get('availability', 0)
        x['availability'] = '{}%'.format(int(100 * avail))
        return x
    
    CMD.run(API, 'info', _response_callback=callback, **kwargs)


@click.command()
@click.option('--name', '-n', help="Name of the deployment")
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
        _response_callback=ListingCallback(obj_title='Deployment', expand=expand)
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
@click.option('--params', help="JSON with parameters to be injected in the notebook")
@click.option('--tag', '-t', default='latest',
              help="""Each deployment task runs on top of a Docker image that belongs to the project. """
                   """You may specify the image's Docker tag or let it default to "latest\"""")
@click.option('--n-tasks', '-n', default=1, help="Number of tasks (containers) for deployment replication (default: 1)")
@click.option('--port', help="Host port to be routed to each container's inference service")
@click.option('--env-var', '-e', 'env_vars', multiple=True, help="Environment variable in the form KEY=VALUE")
@click.option('--mount', '-m', 'mounts', multiple=True,
              help="""A host path or docker volume to mount on each deployment container.\n"""
                   """Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>\n"""
                   """Example: /home/user/data:/data:rw\n""")
@click.option(
    '--movers', '--mv', 'movers',  multiple=True, help=
    """Reference to a model version to be mounted on each deployment container. """
    """Syntax: <model_name>:<version_name>. Example: iris-clf:experiment-v1"""
)
@click.option(
    '--resource-profile', '--rp', 'resource_profile', help=
    """Name of a resource profile to be applied for each container. """
    """This profile should be configured in your nha.yaml file"""
)
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
