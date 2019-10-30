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


def _resolve_path(doc_cls, dyr: str, model: str = None, obj_name: str = None, is_dir=False, ignore: bool = False):
    
    files = os.listdir(dyr)
    doc: [Dataset, ModelVersion] = doc_cls(name=obj_name, model=model)
    
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
            "Could not resolve path to {} '{}' under directory {}. Found {} child paths"
            .format(doc_cls.__name__, doc.show(), dyr, len(files))
        )


def data_path(file_name: str = '', model: str = None, dataset: str = None):
    
    """Shortcut for addressing the dataset's directory.
    
    When Noronha starts a container, all requested datasets have their files mounted and organized inside a volume.
    This function provides a standard way of resolving the path to a dataset's directory or files.
    
    :param file_name: Name of the file to be addressed.
           If not specified, then the path to the directory will be returned.
    :param model: Name of the model to which the dataset belongs.
           If you haven't mounted datasets of different models, this parameter may be left out.
    :param dataset: Name of the dataset.
           If you haven't mounted multiple datasets, this parameter may be left out
    
    :returns: A string containing the requested path.
    
    :raise ResolutionError: If the requested dataset is not present,
           or the given reference matched zero ore multiple datasets.
    """
    
    path = _resolve_path(
        doc_cls=Dataset,
        dyr=OnBoard.LOCAL_DATA_DIR,
        model=model,
        obj_name=dataset,
        is_dir=True
    )
    
    return os.path.join(path, file_name)


def model_path(file_name: str = '', model: str = None, version: str = None, pretrain=False):
    
    """Shortcut for addressing the models directory"""
    
    path = _resolve_path(
        doc_cls=ModelVersion,
        dyr=OnBoard.LOCAL_PRET_MODEL_DIR if pretrain else OnBoard.LOCAL_DEPL_MODEL_DIR,
        model=model,
        obj_name=version,
        is_dir=True
    )
    
    return os.path.join(path, file_name)


def depl_mdl_path(file_name: str = '', version: str = None, model: str = None):
    
    """Shortcut for addressing the deployed model directory
    
    When Noronha starts a container for deployment or IDE usage, all model versions that may be used for prediction
    are mounted and organized inside a volume. Those are called *deployed model versions*. This function provides a
    standard way of resolving the path to the directory or files of one of this model versions.
    
    :param file_name: Name of the file to be addressed.
           If not specified, then the path to the directory will be returned.
    :param model: Name of the model to which the version belongs.
           If you haven't deployed versions of different models, this parameter may be left out.
    :param version: Name of the version.
           If you haven't deployed multiple model versions, this parameter may be left out.
    
    :returns: A string containing the requested path.
    
    :raise ResolutionError: If the requested model version is not present,
           or the given reference matched zero ore multiple model versions.
    """
    
    return model_path(file_name, model, version, pretrain=False)


def pret_mdl_path(file_name: str = '', version: str = None, model: str = None):
    
    """Shortcut for addressing the deployed model directory
    
    When Noronha starts a container for training or IDE usage, all model versions that may be used as pre-trained assets
    are mounted and organized inside a volume. Those are called *pre-trained model versions*. This function provides a
    standard way of resolving the path to the directory or files of one of this model versions.
    
    :param file_name: Name of the file to be addressed.
           If not specified, then the path to the directory will be returned.
    :param model: Name of the model to which the version belongs.
           If you haven't mounted versions of different models, this parameter may be left out.
    :param version: Name of the version.
           If you haven't mounted multiple model versions, this parameter may be left out.
    
    :returns: A string containing the requested path.
    
    :raise ResolutionError: If the requested model version is not present,
           or the given reference matched zero ore multiple model versions.
    """
    
    return model_path(file_name, model, version, pretrain=True)


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


def dataset_meta(model: str = None, dataset: str = None, ignore: bool = False):
    
    """Shortcut for loading the dataset's metadata
    
    When Noronha starts a container, all requested datasets have their metadata mounted and organized inside a volume.
    This function provides a standard way of loading this metadata.
    
    :param model: Name of the model to which the dataset belongs.
           If you haven't mounted datasets of different models, this parameter may be left out.
    :param dataset: Name of the dataset.
           If you haven't mounted multiple datasets, this parameter may be left out.
    :param ignore: If it fails, return an empty document and do not raise exceptions.
    
    :returns: A Dataset document.
    
    :raise ResolutionError: If the requested dataset is not present,
           or the given reference matched zero ore multiple datasets.
    """
    
    return _resolve_metadata(
        doc_cls=Dataset,
        model=model,
        obj_name=dataset,
        ignore=ignore
    )


def movers_meta(model: str = None, version: str = None, ignore: bool = False):
    
    """Shortcut for loading the model versions's metadata
    
    When Noronha starts a container, all requested model versions
    have their metadata mounted and organized inside a volume.
    This function provides a standard way of loading this metadata.
    
    :param model: Name of the model to which the version belongs.
           If you haven't mounted/deployed versions of different models, this parameter may be left out.
    :param version: Name of the version.
           If you haven't mounted multiple model versions, this parameter may be left out.
    :param ignore: If it fails, return an empty document and do not raise exceptions.
    
    :returns: A ModelVersion document.
    
    :raise ResolutionError: If the requested model version is not present,
           or the given reference matched zero ore multiple model versions.
    """
    
    return _resolve_metadata(
        doc_cls=ModelVersion,
        model=model,
        obj_name=version,
        ignore=ignore
    )
