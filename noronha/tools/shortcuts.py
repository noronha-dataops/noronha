# -*- coding: utf-8 -*-

import os

from noronha.common.constants import EnvVar, OnBoard, Paths, DockerConst


def tmp_path(file_name: str = ''):
    
    return os.path.join(Paths.TMP, file_name)


def data_path(file_name: str = ''):
    
    """Shortcut for addressing the datasets directory"""
    
    return os.path.join(OnBoard.LOCAL_DATA_DIR, file_name)


def model_path(file_name: str = '', pretrain=False):
    
    """Shortcut for addressing the models directory"""
    
    dyr = OnBoard.LOCAL_PRET_MODEL_DIR if pretrain else OnBoard.LOCAL_DEPL_MODEL_DIR
    return os.path.join(dyr, file_name)


def pret_mdl_path(file_name: str = ''):
    
    """Shortcut for addressing the pre-trained model directory"""
    
    return model_path(file_name, pretrain=True)


def depl_mdl_path(file_name: str = ''):
    
    """Shortcut for addressing the deployed model directory"""
    
    return model_path(file_name, pretrain=False)


def get_purpose():
    
    purpose = os.environ.get(EnvVar.CONTAINER_PURPOSE) or None
    assert purpose in DockerConst.Section.ALL or purpose is None
    return purpose
