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
import pkg_resources

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
from noronha.cli.tchest import tchest
from noronha.cli.train import train
from noronha.common.constants import FrameworkConst
from noronha.common.logging import LoggerHub, LOG


@click.group()
@click.option('--skip-questions', '-s', default=False, type=bool, is_flag=True, help="Skip questions")
@click.option('--log-level', '-l', default='INFO', type=str, help="Level of log verbosity (DEBUG, INFO, WARN, ERROR)")
@click.option('--debug', '-d', default=False, type=bool, is_flag=True, help="Set log level to DEBUG")
@click.option('--pretty', '-p', default=False, type=bool, is_flag=True, help="Less compact, more readable output")
@click.option('--background', '-b', default=False, type=bool, is_flag=True, help="Run in background, only log to files")
@click.pass_context
def nha(_, skip_questions: bool, log_level: str, debug: bool, pretty: bool, background: bool):
    
    """Command line interface for Noronha DataOps framework"""
    
    CMD.interactive_mode = not skip_questions
    
    if debug:
        log_level = 'DEBUG'
    
    LoggerHub.configure('level', log_level)
    LoggerHub.configure('pretty', pretty)
    LoggerHub.configure('background', background)


@click.command()
def version():
    
    """Framework's version"""
    
    LOG.echo("Noronha Dataops v%s" % FrameworkConst.FW_VERSION)
    pkg = pkg_resources.require(FrameworkConst.FW_NAME)[0]
    
    try:
        meta = pkg.get_metadata_lines('METADATA')
    except FileNotFoundError:
        meta = pkg.get_metadata_lines('PKG-INFO')
    
    for line in meta:
        if not line.startswith('Requires'):
            LOG.info(line)


@click.command()
def get_me_started(**kwargs):
    
    """Initial framework configuration"""
    
    CMD.run(
        IslandAPI, 'get_me_started', **kwargs
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
    tchest,
    train,
    model,
    get_me_started,
    version
]

for cmd in commands:
    nha.add_command(cmd)

nha(obj={})
