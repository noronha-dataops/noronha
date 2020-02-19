# -*- coding: utf-8 -*-

import os

from noronha.common.constants import EnvVar


def am_i_on_board():
    
    return os.environ.get(EnvVar.ON_BOARD, False)


def is_it_open_sea():
    
    return os.environ.get(EnvVar.OPEN_SEA, False)
