# -*- coding: utf-8 -*-

import click
from noronha.common.constants import TMPL_PURPOSE_DOCKER, TMPL_PURPOSE_NOTE
from noronha.core.api import TemplateAPI as API
from noronha.cli._utils import CommandHandler as CMD


@click.group()
def tmpl():
    
    """Templates."""


@click.group()
def note():
    
    """Notebook templates for training, prediction, etc"""
    
    API.set_purpose(major=TMPL_PURPOSE_NOTE)


@click.group()
def docker():
    
    """Dockerfile templates for project encapsulation."""
    
    API.set_purpose(major=TMPL_PURPOSE_DOCKER)


@click.command()
@click.option('--class-name', '-c', 'fqcn',
              help="Fully qualified name of a class that extends noronha.core.tmpl.Tmpl.")
@click.option('--src-path', '-p',
              help="Optional: path to a directory where the class should be correctly loaded " +
                   "(default: current directory).")
def new(**kwargs):
    
    """Adds a new template to the database."""
    
    CMD.run(API, 'new', **kwargs)


@click.command('apply')
@click.option('--name-or-id', '-x', required=True, help="Name or ID of an existing template.")
@click.option('--params', '-p', default={}, help="JSON with parameters for applying this template.")
@click.option('--path', 'target_path', help="Path to the directory where the template will be applied.")
def _apply(**kwargs):
    
    """Applies a template to target directory."""
    
    CMD.run(API, 'apply', **kwargs)


@click.command('list')
@click.option('--filter', '-f', '_filter', default={}, help="Query in JSON syntax (ex: '{\"name\": \"abc\"}').")
def _list(**kwargs):
    
    """Lists the templates in the database."""
    
    CMD.run(API, 'list', _response_callback=shorten_tmpl, **kwargs)


commands = [new, _apply, _list]
groups = [note, docker]

for grp in groups:
    
    tmpl.add_command(grp)
    
    for cmd in commands:
        grp.add_command(cmd)


def shorten_tmpl(x):
    
    x.pop('files', None)
    x.pop('class_name', None)
    return x
