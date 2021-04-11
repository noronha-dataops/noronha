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

import json
import logging
from collections import OrderedDict
from datetime import datetime
from typing import List

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


def join_dicts(parent_dyct, child_dyct, allow_overwrite=False, allow_new_keys=True):
    
    if not child_dyct:
        return parent_dyct
    
    if not allow_new_keys:
        allow_overwrite = True
    
    dyct = parent_dyct.copy()
    
    for k, v in child_dyct.items():
        if k in dyct and not allow_overwrite:
            raise KeyError("Duplicated dict key: {}".format(k))
        elif k not in dyct and not allow_new_keys:
            raise KeyError("Unexpected dict key: {}".format(k))
        else:
            dyct[k] = v
    
    return dyct


def assert_dict(x, allow_none=False):
    
    if x is None:
        if allow_none:
            return {}
        else:
            raise ValueError("Expected str, bytes or dict. Got None")
    elif isinstance(x, dict):
        return x
    else:
        x = assert_str(x).strip()
        return json.loads(x)


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


def assert_extension(x, ext):
    
    if not x.endswith(ext):
        x = x + '.' + ext
    
    return x


def resolve_log_level(lvl: (str, int)):
    
    if isinstance(lvl, int):
        return lvl
    elif isinstance(lvl, str):
        return getattr(logging, lvl.strip().upper())
    else:
        raise TypeError("Cannot resolve log level from reference '{}' of type {}".format(lvl, type(lvl)))
