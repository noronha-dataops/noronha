# -*- coding: utf-8 -*-

import hashlib
import json
import os
from collections import OrderedDict
from datetime import datetime
from subprocess import Popen, PIPE
from typing import List

from noronha.common import EnvVar
from noronha.common.constants import Encoding, DateFmt, Regex


class StructCleaner(object):
    
    def __init__(self, depth=1, nones: list = None):
        
        self.depth = depth
        self.nones = nones or [None, [], {}, (), '']
    
    def __call__(self, x, _depth=5):
        
        if isinstance(x, (dict, OrderedDict)) and _depth > 0:
            return self.clear_dict(x, _depth - 1)
        elif isinstance(x, (list, tuple)):
            return self.clear_list(x, _depth - 1)
        else:
            return x
    
    def clear_dict(self, x, _depth: int):
        
        out = dict()
        
        for k, v in x.items():
            v = self(v, _depth=_depth)
            
            if v not in self.nones:
                out[k] = v
        
        return dict(out)
    
    def clear_list(self, x, _depth: int):
        
        out = []
        
        for v in x:
            v = self(v, _depth=_depth)
            
            if v not in self.nones:
                out.append(v)
        
        return out


def order_yaml(yaml: str):
    
    index = [0] + [i.start() for i in Regex.YAML_BREAK.finditer(yaml)] + [None]
    parts = [yaml[index[i]:index[i+1]].strip() for i in range(len(index)-1)]
    pairs = sorted([(len(p), p) for p in parts], key=lambda p: p[0])
    return '\n'.join([p[1] for p in pairs])


def cape_list(lyst: List[str], max_chars: int = 100):
    
    lyst = str(lyst)[1:-1]
    suffix = '...' if len(lyst) > max_chars else ''
    return lyst[:max_chars] + suffix


def kv_list_to_dict(x: list):
    
    return dict([
        (k, v) for k, v in
        [assert_str(y, allow_empty=False).split('=') for y in x]
    ])


def dict_to_kv_list(x: (dict, OrderedDict)):
    
    return [
        '{0}={1}'.format(key, value)
        for key, value in x.items()
    ]


def join_dicts(parent_dyct, child_dyct, allow_overwrite=False):
    
    if not child_dyct:
        return parent_dyct
    
    dyct = parent_dyct.copy()
    
    for k, v in child_dyct.items():
        if k in dyct and not allow_overwrite:
            raise KeyError("Duplicated dict key: {}".format(k))
        else:
            dyct[k] = v
    
    return dyct


def assert_dict(x, allow_lists=False, allow_none=False, ignore=False):
    
    if x is None and (allow_none or ignore):
        return {}
    
    if isinstance(x, dict):
        return x
    
    try:
        x = assert_str(x).strip()
        x = json.loads(x)
    except Exception:
        pass
    
    if isinstance(x, dict):
        return x
    elif isinstance(x, list) and allow_lists:
        return x
    
    if ignore:
        return x
    else:
        raise TypeError("Could not convert '{}' to dict" .format(x))


def assert_json(x, depth=0, indent=None, encode=False, encoding=None):
    
    if isinstance(x, list):
        x = [assert_json(y, depth + 1) for y in x]
    elif isinstance(x, dict):
        x = dict([(k, assert_json(v, depth + 1)) for k, v in x.items()])
    elif isinstance(x, datetime):
        x = x.strftime(DateFmt.READABLE)
    if depth == 0:
        x = json.dumps(x, indent=indent, ensure_ascii=False)
        return x if not encode else x.encode(encoding)
    else:
        return x


def assert_str(x, encoding=Encoding.UTF_8, allow_none=False, allow_empty=True):
    
    if x is None:
        if allow_none and allow_empty:
            return ''
        else:
            raise TypeError("Cannot coerce None to str")
    
    if isinstance(x, bytes):
        x = x.decode(encoding)
    
    elif not isinstance(x, str):
        x = str(x)
    
    if len(x) == 0 and not allow_empty:
        raise ValueError("Expected a non empty str")
    
    return x


def dict_to_hash(x: dict):
    
    j = assert_json(x, encode=True, encoding=Encoding.UTF_8)
    return hashlib.sha224(j).hexdigest()


def assert_extension(x, ext):
    
    if not x.endswith(ext):
        x = x + '.' + ext
    
    return x


def run_bash_cmd(cmd):
    
    if isinstance(cmd, str):
        cmd = cmd.split(' ')
    
    out, err = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    
    if err:
        raise RuntimeError(assert_str(err).strip())
    else:
        return assert_str(out).strip()


def am_i_on_board():
    
    return os.environ.get(EnvVar.ON_BOARD, False)


def is_it_open_sea():
    
    return os.environ.get(EnvVar.OPEN_SEA, False)
