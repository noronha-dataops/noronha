# -*- coding: utf-8 -*-

import os
from abc import ABC, abstractmethod
from typing import List

from noronha.bay.warehouse import get_warehouse
from noronha.common.constants import WarehouseConst, Extension
from noronha.common.errors import NhaStorageError
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.proj import Project
from noronha.db.utils import FileDoc


class Barrel(ABC):
    
    section: str = None
    
    def __init__(self, schema: List[FileDoc]):
        
        self.warehouse = get_warehouse(section=self.section)
        self.schema = schema
    
    def store_from_dict(self, files: dict = None):
        
        for file_spec in self.schema:
            file_content = files.get(file_spec.name)
            
            if file_content is None:
                if file_spec.required:
                    raise NhaStorageError("File '{}' is required".format(file_spec.name))
                else:
                    continue
            else:
                self._store_file(file_spec.name, content=file_content)
    
    def store_from_path(self, path):
        
        for file_spec in self.schema:
            file_path = os.path.join(path, file_spec.name)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                if file_spec.required:
                    raise NhaStorageError("File '{}' not found in path: {}".format(file_spec.name, path))
                else:
                    continue
            else:
                self._store_file(file_spec.name, path_from=file_path)
    
    def _store_file(self, file_name, **kwargs):
        
        self.warehouse.upload(
            path_to=self.make_file_path(file_name),
            **kwargs
        )
    
    def purge(self, ignore=False):
        
        purged = [
            self.warehouse.delete(self.make_file_path(file_spec.name), ignore=ignore)
            for file_spec in self.schema
        ]
        
        if True not in purged:
            return 'not_found'
        elif False not in purged:
            return 'purged'
        else:
            return 'partial'
    
    def deploy(self, path_to):
        
        deployed = [
            self.warehouse.download(
                path_from=self.make_file_path(file_spec.name),
                path_to=os.path.join(path_to, file_spec.name)
            )
            for file_spec in self.schema
        ]
        
        if True not in deployed:
            return 'not_found'
        elif False not in deployed:
            return 'deployed'
        else:
            return 'partial'
    
    def get_deployables(self, path_to):
        
        return [
            self.warehouse.get_download_cmd(
                path_from=self.make_file_path(file_spec.name),
                path_to=os.path.join(path_to, file_spec.name)
            )
            for file_spec in self.schema
        ]
    
    @abstractmethod
    def make_file_path(self, file_name):
        
        pass


class DatasetBarrel(Barrel):
    
    section = WarehouseConst.Section.DATASETS
    
    def __init__(self, ds: Dataset):
        
        self.ds_name = ds.name
        self.model_name = ds.model.name
        super().__init__(schema=ds.model.data_files)
    
    def make_file_path(self, file_name):
        
        return '{}/{}/{}'.format(self.model_name, self.ds_name, file_name)


class MoversBarrel(Barrel):
    
    section = WarehouseConst.Section.MODELS
    
    def __init__(self, mv: ModelVersion):
        
        self.mv_name = mv.name
        self.model_name = mv.model.name
        super().__init__(schema=mv.model.model_files)
    
    def make_file_path(self, file_name):
        
        return '{}/{}/{}'.format(self.model_name, self.mv_name, file_name)


class NotebookBarrel(Barrel):
    
    section = WarehouseConst.Section.NOTES
    
    def __init__(self, proj: Project, notebook: str, file_name: str):
        
        self.proj_name = proj.name
        self.notebook = notebook.rstrip(Extension.IPYNB).rstrip('.')
        super().__init__(
            schema=[
                FileDoc(name=file_name, required=True)
            ]
        )
    
    def make_file_path(self, file_name):
        
        return '{}/{}/{}'.format(self.proj_name, self.notebook, file_name)
