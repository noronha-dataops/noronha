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

"""TODO: {{module description}}
"""

import os
import pathlib
import shutil
import tarfile
from abc import ABC, abstractmethod
from typing import List

from noronha.bay.warehouse import get_warehouse
from noronha.bay.utils import Workpath, FileSpec, StoreHierarchy
from noronha.common.constants import WarehouseConst, Extension
from noronha.common.errors import NhaStorageError
from noronha.common.logging import Logged
from noronha.common.parser import cape_list
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.proj import Project


class Barrel(ABC, Logged):
    
    section: str = None
    subject = None
    
    def __init__(self, schema: List[FileSpec] = None, compress_to: str = None, log=None, lightweight=False):
        
        Logged.__init__(self, log=log)
        self.warehouse = get_warehouse(section=self.section, log=log, lightweight=lightweight)
        self.compressed = None if not compress_to else '{}.tar.gz'.format(compress_to)
        
        if schema is None:
            self.schema = None
        elif isinstance(schema, list):
            if len(schema) == 0:
                self.schema = None
            else:
                self.schema = [FileSpec.from_doc(d) for d in schema]
        else:
            raise NotImplementedError()
    
    def _print_files(self, schema: List[FileSpec]):
        
        files = [f.name for f in schema]
        caped = cape_list(files)
        self.LOG.info("Files: {}".format(caped))
    
    def infer_schema_from_dict(self, dyct):
        
        if self.schema is None:
            schema = [FileSpec(name=name) for name in dyct.keys()]
            self._print_files(schema)
            return schema
        else:
            return self.schema
    
    def infer_schema_from_path(self, path):
        
        assert os.path.exists(path), NhaStorageError("Path not found: {}".format(path))
        
        if self.schema is None:
            if os.path.isdir(path):
                schema = [FileSpec(name=name) for name in os.listdir(path)]
            else:
                schema = [FileSpec(name=os.path.basename(path))]
                path = os.path.dirname(path)
            self._print_files(schema)
        else:
            schema = self.schema
            
            if os.path.isfile(path):
                if len(schema) == 1:
                    schema = [FileSpec(name=schema[0].name, alias=os.path.basename(path))]
                    path = os.path.dirname(path)
                    self.LOG.warn("File '{}' will be renamed to '{}'".format(schema[0].alias, schema[0].name))
                else:
                    n_reqs = len(list(filter(lambda f: f.required, schema)))
                    assert n_reqs == 1, NhaStorageError("Cannot find all required files in path {}".format(path))
        
        return path, schema
    
    def infer_schema_from_repo(self):
        
        if self.schema is None:
            self.LOG.warn("Deploying {} without a strict definition of files".format(self.subject))
            schema = [
                FileSpec(name=name) for name in
                self.warehouse.lyst(self.make_hierarchy())
            ]
            self._print_files(schema)
        else:
            schema = self.schema
        
        return schema
    
    def raise_for_file_size(self, file_spec: FileSpec, actual_size_mb: int):
        
        raise NhaStorageError(
            "File {} is too large: {} MB"
            .format(file_spec.name, actual_size_mb)
        )
    
    def validate_file_sizes(self, file_schema: List[FileSpec]):
        
        for fyle in file_schema:
            size = fyle.get_size_mb()
            
            if size > fyle.max_mb:
                self.raise_for_file_size(
                    file_spec=fyle,
                    actual_size_mb=size
                )
    
    def store_from_dict(self, dyct: dict = None):
        
        to_compress = []
        to_store = []
        work = None if not self.compressed else Workpath.get_tmp()
        
        try:
            for file_spec in self.infer_schema_from_dict(dyct):
                file_content = dyct.get(file_spec.name)
                
                if file_content is None:
                    if file_spec.required:
                        raise NhaStorageError("File '{}' is required".format(file_spec.name))
                    else:
                        continue
                elif self.compressed:
                    work.deploy_text_file(name=file_spec.name, content=file_content)
                    to_compress.append(file_spec)
                else:
                    file_spec.content = file_content
                    to_store.append(file_spec)
            
            if self.compressed:
                self._compress_and_store(work, to_compress=to_compress)
            else:
                self.validate_file_sizes(to_store)
                self.warehouse.store_files(
                    hierarchy=self.make_hierarchy(),
                    file_schema=to_store
                )
        finally:
            if work is not None:
                work.dispose()
    
    def store_from_path(self, path):
        
        path, schema = self.infer_schema_from_path(path)
        to_compress = []
        to_store = []
        
        for file_spec in schema:
            file_path = os.path.join(path, file_spec.alias)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                if file_spec.required:
                    raise NhaStorageError("File '{}' not found in path: {}".format(file_spec.name, path))
                else:
                    self.LOG.info('Ignoring absent file: {}'.format(file_spec.name))
                    continue
            elif self.compressed:
                to_compress.append(file_spec)
            else:
                file_spec.set_path(path)
                to_store.append(file_spec)
        
        if self.compressed:
            self._compress_and_store(path, to_compress=to_compress)
        else:
            self.validate_file_sizes(to_store)
            self.warehouse.store_files(
                hierarchy=self.make_hierarchy(),
                file_schema=to_store
            )
    
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
    
    def purge(self, ignore=False):
        
        return self.warehouse.delete(
            self.make_hierarchy(),
            ignore=ignore
        )
    
    def _compress_and_store(self, path: str, to_compress: List[FileSpec] = None):
        
        work = Workpath.get_tmp()
        
        try:
            target = work.join(self.compressed)
            
            with tarfile.open(target, 'w:gz') as f:
                for file_spec in to_compress:
                    file_path = os.path.join(path, file_spec.alias)
                    f.add(file_path, arcname=file_spec.name)
            
            file_spec = FileSpec(name=self.compressed)
            self.validate_file_sizes([file_spec])
            self.warehouse.store_files(
                hierarchy=self.make_hierarchy(),
                file_schema=[file_spec]
            )
        finally:
            work.dispose()
    
    def _decompress(self, path: str):
        
        if self.compressed:
            target_file = os.path.join(path, self.compressed)
            
            with tarfile.open(target_file, 'r:gz') as f:
                f.extractall(path)
            
            os.remove(target_file)
    
    def _verify_schema(self, path: str):
        
        if self.schema:
            for file_spec in self.schema:
                file_exists = os.path.isfile(os.path.join(path, file_spec.name))
                assert file_exists or not file_spec.required,\
                    NhaStorageError("Required file '{}' is missing from {}".format(file_spec.name, self.subject))
    
    def deploy(self, path_to):
        
        if self.compressed:
            file_schema = [FileSpec(name=self.compressed)]
        else:
            file_schema = self.infer_schema_from_repo()
        
        self.warehouse.deploy_files(
            hierarchy=self.make_hierarchy(),
            file_schema=file_schema,
            path_to=path_to
        )
        
        self._decompress(path_to)
        self._verify_schema(path_to)
    
    def get_deployables(self, path_to, on_board_perspective=True):
        
        if self.compressed:
            file_schema = [FileSpec(name=self.compressed)]
        else:
            file_schema = self.infer_schema_from_repo()
        
        hierarchy = self.make_hierarchy()
        
        cmds = [
            self.warehouse.get_download_cmd(
                path_from=hierarchy.join_as_path(file_spec.name),
                path_to=os.path.join(path_to, file_spec.name),
                on_board_perspective=on_board_perspective
            )
            for file_spec in file_schema
        ]
        
        msgs = [
            'Injecting file: {}'.format(file_spec.name)
            for file_spec in file_schema
        ]
        
        if self.compressed:
            msgs.append('Extracting {} to {}'.format(self.compressed, path_to))
            cmds.append('tar -xzf {tgz_file} {path} && rm -f {tgz_file}'.format(
                tgz_file=self.compressed,
                path=path_to
            ))
        
        return zip(msgs, cmds)
    
    @abstractmethod
    def make_hierarchy(self) -> StoreHierarchy:
        
        pass


class DatasetBarrel(Barrel):
    
    section = WarehouseConst.Section.DATASETS
    
    def __init__(self, ds: Dataset, **kwargs):
        
        self.ds_name = ds.name
        self.model_name = ds.model.name
        self.subject = "dataset '{}'".format(ds.show())
        super().__init__(
            schema=ds.model.data_files,
            compress_to=None if not ds.compressed else ds.name,
            lightweight=ds.lightweight,
            **kwargs
        )
    
    def make_hierarchy(self) -> StoreHierarchy:
        
        return StoreHierarchy(
            parent=self.model_name,
            child=self.ds_name
        )

    def raise_for_file_size(self, file_spec: FileSpec, actual_size_mb: int):
        
        raise NhaStorageError(
            "File {} in dataset '{}' of model '{}' is too large (expected size={} MB / actual size={} MB)"
            .format(file_spec.name, self.ds_name, self.model_name, file_spec.max_mb, actual_size_mb)
        )


class MoversBarrel(Barrel):
    
    section = WarehouseConst.Section.MODELS
    
    def __init__(self, mv: ModelVersion, **kwargs):
        
        self.mv_name = mv.name
        self.model_name = mv.model.name
        self.subject = "model version '{}'".format(mv.show())
        super().__init__(
            schema=mv.model.model_files,
            compress_to=None if not mv.compressed else mv.name,
            lightweight=mv.lightweight,
            **kwargs
        )
    
    def make_hierarchy(self) -> StoreHierarchy:
        
        return StoreHierarchy(
            parent=self.model_name,
            child=self.mv_name
        )

    def raise_for_file_size(self, file_spec: FileSpec, actual_size_mb: int):
        
        raise NhaStorageError(
            "File {} in version '{}' of model '{}' is too large (expected size={} MB / actual size={} MB)"
            .format(file_spec.name, self.mv_name, self.model_name, file_spec.max_mb, actual_size_mb)
        )
 

class NotebookBarrel(Barrel):
    
    section = WarehouseConst.Section.NOTES
    
    def __init__(self, proj: Project, notebook: str, file_name: str):
        
        self.proj_name = proj.name
        self.notebook = notebook.rstrip(Extension.IPYNB).rstrip('.')
        self.subject = "notebook '{}'".format(self.notebook)
        super().__init__(
            schema=[
                FileSpec(name=file_name, required=True)
            ]
        )
    
    def make_hierarchy(self) -> StoreHierarchy:
        
        return StoreHierarchy(
            parent=self.proj_name,
            child=self.notebook
        )
