# -*- coding: utf-8 -*-

import os

from noronha.common.constants import OnBoard, Paths


def tmp_path(file_name: str = ''):
    
    return os.path.join(Paths.TMP, file_name)


def model_path(file_name):
    
    """Shortcut for addressing the models directory"""
    
    return os.path.join(OnBoard.LOCAL_MODEL_DIR, file_name)


def data_path(file_name):
    
    """Shortcut for addressing the datasets directory"""
    
    return os.path.join(OnBoard.LOCAL_DATA_DIR, file_name)
