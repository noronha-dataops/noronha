# -*- coding: utf-8 -*-

import os
import pathlib
import shutil
from abc import ABC, abstractmethod
from typing import List

from noronha.bay.warehouse import get_warehouse
from noronha.common.constants import WarehouseConst, Extension
from noronha.common.errors import NhaStorageError
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.proj import Project
from noronha.db.utils import FileDoc


class FileSpec(FileDoc):
    
    def __init__(self, alias: str = None, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.alias = alias or self.name
    
    @classmethod
    def from_doc(cls, doc: FileDoc):
        
        return cls(alias=doc.name, **doc.as_dict())


class Barrel(ABC):
    
    section: str = None
    
    def __init__(self, schema: List[FileSpec] = None):
        
        self.warehouse = get_warehouse(section=self.section)
        
        if schema is None:
            self.schema = None
        elif isinstance(schema, list):
            if len(schema) == 0:
                self.schema = None
            else:
                self.schema = [FileSpec.from_doc(d) for d in schema]
        else:
            raise NotImplementedError()
    
    def infer_schema_from_dict(self, dyct):
        
        if self.schema is None:
            return [FileSpec(name=name) for name in dyct.keys()]
        else:
            return self.schema
    
    def infer_schema_from_path(self, path):
        
        assert os.path.exists(path)
        
        if self.schema is None:
            if os.path.isdir(path):
                schema = [FileSpec(name=name) for name in os.listdir(path)]
            else:
                path = os.path.dirname(path)
                schema = [FileSpec(name=os.path.basename(path))]
        else:
            schema = self.schema
            
            if os.path.isfile(path):
                if len(schema) == 1:
                    schema = [FileSpec(name=schema[0].name, alias=os.path.basename(path))]
                else:
                    n_reqs = len(list(filter(lambda f: f.required, schema)))
                    assert n_reqs == 1, NhaStorageError("Cannot find all required files in path {}".format(path))
        
        return path, schema
    
    def infer_schema_from_repo(self):
        
        if self.schema is None:
            return [
                FileSpec(name=name) for name in
                self.warehouse.list_dir(self.make_file_path())
            ]
        else:
            return self.schema
    
    def store_from_dict(self, dyct: dict = None):
        
        for file_spec in self.infer_schema_from_dict(dyct):
            file_content = dyct.get(file_spec.name)
            
            if file_content is None:
                if file_spec.required:
                    raise NhaStorageError("File '{}' is required".format(file_spec.name))
                else:
                    continue
            else:
                self._store_file(file_spec.name, content=file_content)
    
    def store_from_path(self, path):
        
        path, schema = self.infer_schema_from_path(path)
        
        for file_spec in schema:
            file_path = os.path.join(path, file_spec.alias)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                if file_spec.required:
                    raise NhaStorageError("File '{}' not found in path: {}".format(file_spec.name, path))
                else:
                    continue
            else:
                self._store_file(file_spec.name, path_from=file_path)
    
    def move(self, path_from, path_to):
        
        path_from, schema = self.infer_schema_from_path(path_from)
        
        if not os.path.isdir(path_to):
            pathlib.Path(path_to).mkdir(parents=True, exist_ok=True)
        
        for file_spec in schema:
            file_path = os.path.join(path_from, file_spec.name)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                if file_spec.required:
                    raise NhaStorageError("File '{}' not found in path: {}".format(file_spec.name, path_from))
                else:
                    continue
            else:
                shutil.move(file_path, os.path.join(path_to, file_spec.name))
    
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
            for file_spec in self.infer_schema_from_repo()
        ]
        
        if True not in deployed:
            return 'not_found'
        elif False not in deployed:
            return 'deployed'
        else:
            return 'partial'
    
    def get_deployables(self, path_to, on_board_perspective=True):
        
        return [
            self.warehouse.get_download_cmd(
                path_from=self.make_file_path(file_spec.name),
                path_to=os.path.join(path_to, file_spec.name),
                on_board_perspective=on_board_perspective
            )
            for file_spec in self.infer_schema_from_repo()
        ]
    
    @abstractmethod
    def make_file_path(self, file_name: str = None):
        
        pass


class DatasetBarrel(Barrel):
    
    section = WarehouseConst.Section.DATASETS
    
    def __init__(self, ds: Dataset):
        
        self.ds_name = ds.name
        self.model_name = ds.model.name
        super().__init__(schema=ds.model.data_files)
    
    def make_file_path(self, file_name: str = None):
        
        return '{}/{}/{}'.format(self.model_name, self.ds_name, file_name or '')


class MoversBarrel(Barrel):
    
    section = WarehouseConst.Section.MODELS
    
    def __init__(self, mv: ModelVersion):
        
        self.mv_name = mv.name
        self.model_name = mv.model.name
        super().__init__(schema=mv.model.model_files)
    
    def make_file_path(self, file_name: str = None):
        
        return '{}/{}/{}'.format(self.model_name, self.mv_name, file_name or '')


class NotebookBarrel(Barrel):
    
    section = WarehouseConst.Section.NOTES
    
    def __init__(self, proj: Project, notebook: str, file_name: str):
        
        self.proj_name = proj.name
        self.notebook = notebook.rstrip(Extension.IPYNB).rstrip('.')
        super().__init__(
            schema=[
                FileSpec(name=file_name, required=True)
            ]
        )
    
    def make_file_path(self, file_name: str = None):
        
        return '{}/{}/{}'.format(self.proj_name, self.notebook, file_name or '')
