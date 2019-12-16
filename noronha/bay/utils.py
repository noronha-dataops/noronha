# -*- coding: utf-8 -*-

import os
import pathlib
import random_name
from shutil import rmtree

from noronha.common.constants import Paths, EnvVar


def am_i_on_board():
    
    return os.environ.get(EnvVar.ON_BOARD, False)


def is_it_open_sea():
    
    return os.environ.get(EnvVar.OPEN_SEA, False)


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
