# -*- coding: utf-8 -*-

import re

from noronha.common.utils import run_bash_cmd

READ_ONLY = ['info', 'list']
READ_RM = READ_ONLY + ['rm']
CRUD_ONCE = READ_RM + ['new']
CRUD_FULL = CRUD_ONCE + ['update']

cmd_map = {
    'proj': {'title': 'Project', 'commands': CRUD_FULL + ['build']},
    'bvers': {'title': 'Build Version', 'commands': READ_RM},
    'model': {'title': 'Model', 'commands': CRUD_FULL},
    'ds': {'title': 'Dataset', 'commands': CRUD_FULL},
    'train': {'title': 'Training', 'commands': CRUD_ONCE},
    'movers': {'title': 'Model Version', 'commands': CRUD_FULL},
    'depl': {'title': 'Deployment', 'commands': CRUD_ONCE}
}

RE_TEXT = re.compile(r' *TEXT')
RE_SPACE = re.compile(r'\s{2,}')
RE_REQUIRED = re.compile(r' *\[required\] *')


def parse_arg(arg: str):
    
    arg = arg.strip()
    arg = RE_TEXT.sub('', arg)
    arg = RE_REQUIRED.sub('', arg)
    
    try:
        name, desc = RE_SPACE.split(arg, 1)
    except ValueError as e:
        if str(e).strip() == 'not enough values to unpack (expected 2, got 1)':
            desc = arg
            name = ''
        else:
            raise e
    
    return name, desc


def parse_args(args: list):
    
    max_name_len = 0
    names = []
    descs = []
    
    for arg in args:
        name, desc = parse_arg(arg)
        max_name_len = max(max_name_len, len(name))
        names.append(name)
        descs.append(desc)
    
    return '\n'.join([
        '    {name}{indent}{desc}'.format(
            name=name,
            desc=desc,
            indent=' '*(max_name_len - len(name) + 4)
        )
        for name, desc in zip(names, descs)
    ])


doc = []

for subject, details in cmd_map.items():
    
    default_desc = 'Reference for commands under the subject *{}*.'.format(subject)
    doc.append(details.get('title', subject))
    doc.append('===============')
    doc.append(details.get('desc', default_desc))
    doc.append('')
    
    for cmd in details['commands']:
        out = run_bash_cmd('nha {0} {1} --help'.format(subject, cmd)).split('\n')
        doc.append('- **{0}:** {1}'.format(cmd, out[2].strip()))
        doc.append('')
        doc.append('.. parsed-literal::')
        doc.append('')
        doc.append(parse_args(out[5:-1]))
        doc.append('')

with open('cli_auto-generated.rst', 'w') as f:
    f.write('\n'.join(doc))
