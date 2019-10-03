# -*- coding: utf-8 -*-

import os

from noronha.common.constants import EnvVar, OnBoard, Paths, DockerConst
from noronha.common.errors import ResolutionError
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion


def get_purpose():
    
    purpose = os.environ.get(EnvVar.CONTAINER_PURPOSE) or None
    assert purpose in DockerConst.Section.ALL or purpose is None
    return purpose


def tmp_path(file_name: str = ''):
    
    return os.path.join(Paths.TMP, file_name)


def _resolve_path(doc_cls, dyr: str, model_name: str = None, obj_name: str = None, is_dir=False, ignore: bool = False):
    
    files = os.listdir(dyr)
    doc: [Dataset, ModelVersion] = doc_cls(name=obj_name, model=model_name)
    
    if is_dir:
        regex = doc.get_dir_name_regex()
    else:
        regex = doc.get_file_name_regex()
    
    match = list(filter(lambda f: regex.match(f), files))
    
    if len(match) == 1:
        return os.path.join(dyr, match[0])
    elif ignore:
        return None
    else:
        raise ResolutionError(
            "Could not resolve path to {} under directory {}. Found {} child paths"
            .format(doc_cls.__name__, dyr, len(files))
        )


def data_path(file_name: str = '', model_name: str = None, dataset_name: str = None):
    
    """Shortcut for addressing the datasets directory"""
    
    path = _resolve_path(
        doc_cls=Dataset,
        dyr=OnBoard.LOCAL_DATA_DIR,
        model_name=model_name,
        obj_name=dataset_name,
        is_dir=True
    )
    
    return os.path.join(path, file_name)


def model_path(file_name: str = '', model_name: str = None, version_name: str = None, pretrain=False):
    
    """Shortcut for addressing the models directory"""
    
    path = _resolve_path(
        doc_cls=ModelVersion,
        dyr=OnBoard.LOCAL_PRET_MODEL_DIR if pretrain else OnBoard.LOCAL_DEPL_MODEL_DIR,
        model_name=model_name,
        obj_name=version_name,
        is_dir=True
    )
    
    return os.path.join(path, file_name)


def pret_mdl_path(file_name: str = '', version_name: str = None, model_name: str = None):
    
    """Shortcut for addressing the pre-trained model directory"""
    
    return model_path(file_name, model_name, version_name, pretrain=True)


def depl_mdl_path(file_name: str = '', version_name: str = None, model_name: str = None):
    
    """Shortcut for addressing the deployed model directory"""
    
    return model_path(file_name, model_name, version_name, pretrain=False)


def _resolve_metadata(doc_cls, ignore: bool = False, **kwargs):
    
    path = _resolve_path(
        doc_cls=doc_cls,
        dyr=OnBoard.META_DIR,
        ignore=ignore,
        **kwargs
    )
    
    if path is None:
        return doc_cls()
    else:
        return doc_cls.load(path)


def dataset_meta(model_name: str = None, dataset_name: str = None, ignore: bool = False):
    
    return _resolve_metadata(
        doc_cls=Dataset,
        model_name=model_name,
        obj_name=dataset_name,
        ignore=ignore
    )


def movers_meta(model_name: str = None, version_name: str = None, ignore: bool = False):
    
    return _resolve_metadata(
        doc_cls=ModelVersion,
        model_name=model_name,
        obj_name=version_name,
        ignore=ignore
    )
