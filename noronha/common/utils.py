# -*- coding: utf-8 -*-

import os
import shutil

from os.path import isfile

from noronha.common.constants import EnvVar
from noronha.common.errors import MisusageError


def am_i_on_board():
    
    return os.environ.get(EnvVar.ON_BOARD, False)


def is_it_open_sea():
    
    return os.environ.get(EnvVar.OPEN_SEA, False)


class FsHelper(object):

    def __init__(self, path: str):

        self.path = path

    def list_objects(self):

        if not isfile(self.path):
            return os.listdir(self.path)
        else:
            return self.path

    def get_modify_time(self):

        return os.path.getmtime(self.path)

    def delete_path(self):

        if not isfile(self.path):
            shutil.rmtree(self.path)
        else:
            raise MisusageError
