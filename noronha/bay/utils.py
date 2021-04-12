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

import os
import pathlib
import random_name
from shutil import rmtree
from collections import namedtuple

from noronha.common.constants import Paths, Encoding, Regex
from noronha.db.utils import FileDoc


class StoreHierarchy(object):
    
    _NAMED_TUPLE = namedtuple('StoreHierarchy', ['parent', 'child'])
    
    def __init__(self, parent: str, child: str):
        
        self.hierarchy = self._NAMED_TUPLE(parent, child)
    
    @property
    def parent(self):
        
        return self.hierarchy.parent
    
    @property
    def child(self):
        
        return self.hierarchy.child
    
    def join_as_path(self, file_name: str = ''):
        
        return os.path.join(self.parent, self.child, file_name)
    
    def join_as_table_name(self, section: str):
        
        return '_'.join([
            section,
            Regex.DNS_SPECIAL.sub('_', self.parent)
        ])


class FileSpec(FileDoc):

    def __init__(self, alias: str = None, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.alias = alias or self.name
        self.path_from = self.alias
        self.content = None
    
    @classmethod
    def from_doc(cls, doc: FileDoc):
        
        return cls(alias=doc.name, **doc.as_dict())
    
    def set_path(self, path: str):
        
        self.path_from = os.path.join(path, self.alias)
    
    @property
    def kwargs(self):
        
        return dict(
            path_from=self.path_from,
            content=self.content
        )
    
    def get_name_as_table_field(self, include_type=False):
        
        return '{}{}'.format(
            Regex.DNS_SPECIAL.sub('_', self.name),
            ' BLOB' if include_type else ''
        )
    
    def get_bytes(self):

        if self.content is None:
            return open(self.path_from, 'rb').read()
        elif isinstance(self.content, bytes):
            return self.content
        else:
            return self.content.encode(Encoding.DEFAULT)
    
    def get_size_mb(self):
        
        if self.content is None:
            n_bites = os.path.getsize(self.path_from)
        else:
            n_bites = len(self.content)
        
        return int(n_bites/(1024*1024))


class Workpath(str):
    
    def __new__(cls, path, *args, **kwargs):
        
        return super().__new__(cls, path)
    
    def __init__(self, path: str, disposable: bool):
        
        self.disposable = disposable
    
    @classmethod
    def get_tmp(cls):
        
        path = os.path.join(Paths.NHA_WORK, random_name.generate_name())
        pathlib.Path(path).mkdir(parents=True, exist_ok=False)
        return cls(path, disposable=True)
    
    @classmethod
    def get_fixed(cls, path: str):
        
        assert os.path.exists(path) and os.path.isdir(path),\
            NotADirectoryError("Cannot create workpath at: {}".format(path))
        return cls(path, disposable=False)
    
    def dispose(self):
        
        if self.disposable:
            rmtree(self)
            return True
        else:
            return False
    
    def join(self, suffix):
        
        return os.path.join(self, suffix)
    
    def deploy_text_file(self, name, content):
        
        open(self.join(name), 'w').write(content)
    
    def deploy_text_files(self, files: dict):
        
        for file_name, file_content in files.items():
            self.deploy_text_file(name=file_name, content=file_content)
