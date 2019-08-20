# -*- coding: utf-8 -*-

import click
import logging

from noronha.api.island import IslandAPI
from noronha.cli.bvers import bvers
from noronha.cli.depl import depl
from noronha.cli.ds import ds
from noronha.cli.handler import CommandHandler as CMD
from noronha.cli.isle import isle
from noronha.cli.model import model
from noronha.cli.movers import movers
from noronha.cli.note import note
from noronha.cli.proj import proj
from noronha.cli.train import train
from noronha.common.constants import FW_VERSION
from noronha.common.logging import LOG


@click.group()
@click.option('--skip', '-s', default=False, type=bool, is_flag=True, help="Skip questions")
@click.option('--quiet', '-q', default=False, type=bool, is_flag=True, help="Suppress all messages")
@click.option('--verbose', '-v', default=False, type=bool, is_flag=True, help="Show more explicit messages")
@click.option('--debug', '-d', default=False, type=bool, is_flag=True, help="Show logs for debugging purposes")
@click.option('--pretty', '-p', default=False, type=bool, is_flag=True, help="Less compact, more readable")
@click.pass_context
def nha(_, quiet, verbose, debug, pretty, skip):
    
    """Command line interface for Noronha DataOps framework"""
    
    CMD.interactive = not skip
    LOG.setup()
    
    if debug:
        LOG.level = logging.DEBUG
    elif verbose:
        LOG.level = logging.INFO
    elif quiet:
        LOG.level = logging.ERROR
    else:
        LOG.level = logging.WARN
    
    if pretty:
        LOG.pretty = True
        # stackprinter.set_excepthook(style=LOG.conf.get('traceback_style'))


@click.command()
def version():
    
    """Framework's version"""
    
    LOG.echo("Noronha Dataops v%s" % FW_VERSION)


@click.command()
def get_me_started(**kwargs):
    
    """Initial framework configuration"""
    
    CMD.run(
        IslandAPI, 'get_me_started', **kwargs,
        _proj_resolvers=None  # force project resolution skip, since MongoDB may not be running yet
    )


commands = [
    bvers,
    depl,
    ds,
    isle,
    model,
    note,
    movers,
    proj,
    train,
    model,
    get_me_started,
    version
]

for cmd in commands:
    nha.add_command(cmd)

nha(obj={})
