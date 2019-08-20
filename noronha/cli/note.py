# -*- coding: utf-8 -*-

import click
import os

from noronha.api.note import NotebookAPI as API
from noronha.api.utils import ProjResolver
from noronha.cli.handler import CMD
from noronha.common.constants import OnBoard, NoteConst
from noronha.common.utils import kv_list_to_dict


@click.command()
@click.option('--tag', '-t', default='latest',
              help="""The IDE runs on top of a Docker image that belongs to the current working project. """
                   """You may specify the image's Docker tag or let it default to "latest\"""")
@click.option(
    '--port', '-p', default=NoteConst.HOST_PORT,
    help="Host port that will be routed to the notebook's user interface (default: {})".format(NoteConst.HOST_PORT)
)
@click.option('--env-var', '-e', 'env_vars', multiple=True, help="Environment variable in the form KEY=VALUE")
@click.option('--mount', '-m', 'mounts', multiple=True,
              help="""A host path or docker volume to mount on the IDE's container.\n"""
                   """Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>\n"""
                   """Example: /home/user/data:/data:rw\n"""
                   """Obs: current working path is mounted automatically""")
@click.option(
    '--edit', default=False, is_flag=True,
    help="""Flag: also mount current directory into the container's /app directory. This is useful if you want to """
         """edit code, test it and save it in the local machine (WARN: in Kubernetes mode this will only work if """
         """the current directory is part of your NFS server)"""
)
def note(env_vars: list, mounts: list, port: int, edit: bool = False, **kwargs):
    
    """Access to an interactive notebook (IDE)"""
    
    edit_mount = ['{}:{}:rw'.format(os.getcwd(), OnBoard.APP_HOME)] if edit else []
    
    CMD.run(
        API, '__call__', **kwargs,
        _proj_resolvers=[ProjResolver.BY_REPO],
        env_vars=kv_list_to_dict(env_vars),
        mounts=list(mounts) + edit_mount,
        port=int(port)
    )
