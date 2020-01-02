# -*- coding: utf-8 -*-

import os
import pathlib
import shutil
import tarfile
from abc import ABC, abstractmethod
from typing import List

from noronha.bay.warehouse import get_warehouse
from noronha.bay.utils import Workpath
from noronha.common.constants import WarehouseConst, Extension
from noronha.common.errors import NhaStorageError
from noronha.common.logging import Logged
from noronha.common.utils import cape_list
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


class Barrel(ABC, Logged):
    
    section: str = None
    subject = None
    
    def __init__(self, schema: List[FileSpec] = None, compress_to: str = None, log=None):
        
        Logged.__init__(self, log=log)
        self.warehouse = get_warehouse(section=self.section, log=log)
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
        
        assert os.path.exists(path)
        
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
                self.warehouse.list_dir(self.make_file_path())
            ]
            self._print_files(schema)
        else:
            schema = self.schema
        
        return schema
    
    def store_from_dict(self, dyct: dict = None):
        
        to_compress = []
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
                    self._store_file(file_spec.name, content=file_content)
            
            if self.compressed:
                self._compress_and_store(work, to_compress=to_compress)
        finally:
            if work is not None:
                work.dispose()
    
    def store_from_path(self, path):
        
        path, schema = self.infer_schema_from_path(path)
        to_compress = []
        
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
                self._store_file(file_spec.name, path_from=file_path)
        
        if self.compressed:
            self._compress_and_store(path, to_compress=to_compress)
    
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
        
        self.LOG.info("Uploading file: {}".format(file_name))
        self.warehouse.upload(
            path_to=self.make_file_path(file_name),
            **kwargs
        )
    
    def purge(self, ignore=False):
        
        return self.warehouse.delete(
            self.make_file_path(),
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
            
            self._store_file(self.compressed, path_from=target)
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
            download_schema = [FileSpec(name=self.compressed)]
        else:
            download_schema = self.infer_schema_from_repo()
        
        for file_spec in download_schema:
            try:
                self.LOG.info('Downloading file: {}'.format(file_spec.name))
                self.warehouse.download(
                    path_from=self.make_file_path(file_spec.name),
                    path_to=os.path.join(path_to, file_spec.name)
                )
            except NhaStorageError as e:
                if file_spec.required:
                    raise e
                else:
                    self.LOG.info('Ignoring absent file: {}'.format(file_spec.name))
        
        self._decompress(path_to)
        self._verify_schema(path_to)
    
    def get_deployables(self, path_to, on_board_perspective=True):
        
        if self.compressed:
            download_schema = [FileSpec(name=self.compressed)]
        else:
            download_schema = self.infer_schema_from_repo()
        
        cmds = [
            self.warehouse.get_download_cmd(
                path_from=self.make_file_path(file_spec.name),
                path_to=os.path.join(path_to, file_spec.name),
                on_board_perspective=on_board_perspective
            )
            for file_spec in download_schema
        ]
        
        msgs = [
            'Downloading file: {}'.format(file_spec.name)
            for file_spec in download_schema
        ]
        
        if self.compressed:
            msgs.append('Extracting {} to {}'.format(self.compressed, path_to))
            cmds.append('tar -xzf {tgz_file} {path} && rm -f {tgz_file}'.format(
                tgz_file=self.compressed,
                path=path_to
            ))
        
        return zip(msgs, cmds)
    
    @abstractmethod
    def make_file_path(self, file_name: str = None):
        
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
            **kwargs
        )
    
    def make_file_path(self, file_name: str = None):
        
        return '{}/{}/{}'.format(self.model_name, self.ds_name, file_name or '')


class MoversBarrel(Barrel):
    
    section = WarehouseConst.Section.MODELS
    
    def __init__(self, mv: ModelVersion, **kwargs):
        
        self.mv_name = mv.name
        self.model_name = mv.model.name
        self.subject = "model version '{}'".format(mv.show())
        super().__init__(
            schema=mv.model.model_files,
            compress_to=None if not mv.compressed else mv.name,
            **kwargs
        )
    
    def make_file_path(self, file_name: str = None):
        
        return '{}/{}/{}'.format(self.model_name, self.mv_name, file_name or '')


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
    
    def make_file_path(self, file_name: str = None):
        
        return '{}/{}/{}'.format(self.proj_name, self.notebook, file_name or '')
