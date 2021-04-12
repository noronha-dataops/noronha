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

"""Module for handling objects in file systems

Objects handled:
- Model version files (binaries) in Artifactory or in docker volumes
- Notebook output files (pdf) in Artifactory
- Dataset packages
"""
import traceback
import sys
import os
from abc import ABC, abstractmethod
from artifactory import ArtifactoryPath
from cassandra import InvalidRequest
from cassandra.cluster import Cluster
from cassandra.policies import RoundRobinPolicy
from nexuscli import nexus_client
from typing import Type, List
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from noronha.bay.compass import FSWarehouseCompass, ArtifCompass, NexusCompass, LWWarehouseCompass, CassWarehouseCompass,\
                                WarehouseCompass
from noronha.bay.utils import Workpath, FileSpec, StoreHierarchy
from noronha.common.annotations import Configured
from noronha.common.conf import LazyConf
from noronha.common.constants import Config, Perspective, Flag
from noronha.common.errors import ResolutionError, NhaStorageError, MisusageError, ConfigurationError
from noronha.common.logging import Logged


class Warehouse(ABC, Configured, Logged):
    
    compass_cls = WarehouseCompass

    def __init__(self, section: str, log=None):
        
        Logged.__init__(self, log=log)
        self.client = None
        self.section = section
        self.compass = self.compass_cls()
    
    @abstractmethod
    def connect(self):
        
        pass

    @abstractmethod
    def delete(self, hierarchy: StoreHierarchy, ignore=False):
        
        pass

    @abstractmethod
    def get_download_cmd(self, path_from, path_to, on_board_perspective=True):
        
        pass
    
    @abstractmethod
    def lyst(self, path):
        
        pass
    
    @abstractmethod
    def store_files(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec]):
        
        pass
    
    @abstractmethod
    def deploy_files(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec], path_to: str):
        
        pass


class FileStoreWarehouse(Warehouse, ABC):
    
    conf = LazyConf(namespace=Config.Namespace.FS_WAREHOUSE)
    compass_cls = FSWarehouseCompass
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        self.compass: FSWarehouseCompass = self.compass
        self.connect()
        
        if not self.compass.check_certificate:
            disable_warnings(InsecureRequestWarning)
        
        self.assert_repo_exists()
    
    @property
    def repo(self):
        
        return self.compass.get_store()
    
    @property
    def address(self):
        
        return self.compass.address
    
    @abstractmethod
    def assert_repo_exists(self):
        
        pass

    @abstractmethod
    def upload(self, path_to, path_from=None, content=None):

        pass
    
    @abstractmethod
    def download(self, path_from, path_to):

        pass
    
    def make_local_file(self, basename, content):
        work = Workpath.get_tmp()
        work.deploy_text_file(name=basename, content=content)
        path_from = work.join(basename)
        return path_from

    def store_files(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec]):
        
        for file_spec in file_schema:
            self.LOG.info("Uploading file: {}".format(file_spec.name))
            path_to = hierarchy.join_as_path(file_spec.name)
            self.upload(path_to, **file_spec.kwargs)

    def deploy_files(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec], path_to: str):
        
        for file_spec in file_schema:
            try:
                self.LOG.info('Downloading file: {}'.format(file_spec.name))
                self.download(
                    path_from=hierarchy.join_as_path(file_spec.name),
                    path_to=os.path.join(path_to, file_spec.name)
                )
            except NhaStorageError as e:
                if file_spec.required:
                    raise e
                else:
                    self.LOG.info('Ignoring absent file: {}'.format(file_spec.name))


class ArtifWarehouse(FileStoreWarehouse):
    
    compass_cls = ArtifCompass
    
    def connect(self):
        
        self.client = ArtifactoryPath(
            os.path.join(self.address, 'artifactory', self.repo),
            auth=(self.compass.user, self.compass.pswd),
            verify=self.compass.check_certificate
        )
    
    def assert_repo_exists(self):
    
        assert self.client.exists(), NhaStorageError("""The {} repository does not exist""".format(self.repo))
    
    def format_artif_path(self, path):
        
        return self.client.joinpath(self.section, path)
    
    def upload(self, path_to, path_from=None, content=None):
        
        work = None
        
        try:
            if content is not None:
                work = Workpath.get_tmp()
                file_name = os.path.basename(path_to)
                work.deploy_text_file(name=file_name, content=content)
                path_from = work.join(file_name)
            
            dest_path = self.format_artif_path(path_to)
            dest_path.deploy_file(path_from)
        except Exception as e:
            raise NhaStorageError("Upload failed. Check if the artifact´s path is correct") from e
        finally:
            if work is not None:
                work.dispose()
    
    def download(self, path_from, path_to):
        
        uri = self.format_artif_path(path_from)
        
        try:
            with uri.open() as src:
                with open(path_to, "wb") as out:
                    out.write(src.read())
        except Exception as e:
            raise NhaStorageError("Download failed. Check if the remote artifact exists in the repository") from e

    def delete(self, hierarchy: StoreHierarchy, ignore=False):
        
        path = hierarchy.join_as_path()
        uri = self.format_artif_path(path)
        
        try:
            if uri.is_dir():
                uri.rmdir()
            else:
                uri.unlink()
            
            return True
        except FileNotFoundError as e:
            message = "Delete from Artifactory failed. Check if the path exists: {}".format(uri)
            
            if ignore:
                self.LOG.warn(message)
                return False
            else:
                raise NhaStorageError(message) from e
    
    def get_download_cmd(self, path_from, path_to, on_board_perspective=True):
        
        if on_board_perspective:
            compass = self.compass_cls(perspective=Perspective.ON_BOARD)
        else:
            compass = self.compass

        curl = "curl {security} -O -u {user}:{pswd} {url}".format(
            security='' if compass.check_certificate else '--insecure',
            user=compass.user,
            pswd=compass.pswd,
            url=self.format_artif_path(path_from)
        )

        move = "mkdir -p {dir} && mv {file} {path_to}".format(
            dir=os.path.dirname(path_to),
            file=os.path.basename(path_to),
            path_to=os.path.dirname(path_to)
        )

        return ' && '.join([curl, move])
    
    def lyst(self, path):

        path = self.format_artif_path(path)
        return [x.name for x in path.iterdir() if not x.is_dir()]


class NexusWarehouse(FileStoreWarehouse):
    
    compass_cls = NexusCompass
    
    def format_nexus_path(self, path):
        return os.path.join(
            self.address,
            'repository',
            self.repo,
            self.section,
            path
        )
    
    def connect(self):
        
        self.client = nexus_client.NexusClient(
            url=self.address,
            user=self.compass.user,
            password=self.compass.pswd,
            verify=self.compass.check_certificate
        )
    
    def assert_repo_exists(self):
        
        repositories = self.client.repositories.raw_list()
        nexus_repo = list(filter(lambda d: d['name'] == self.repo, repositories))
        assert len(nexus_repo) > 0, NhaStorageError("""The {} repository does not exist""".format(self.repo))
    
    def upload(self, path_to, path_from: (str, None) = None, content: (str, None) = None):
        
        work = None
        
        try:
            if path_from is None:
                work = Workpath.get_tmp()
                file_name = os.path.basename(path_to)
                work.deploy_text_file(name=file_name, content=content)
                path_from = work.join(file_name)
            
            dest_path = os.path.join(self.repo, self.section, path_to)
            self.client.upload(path_from, dest_path)
        except Exception as e:
            raise NhaStorageError("Upload failed. Check if the artifact´s path is correct") from e
        finally:
            if work is not None:
                work.dispose()
    
    def download(self, path_from, path_to):
        
        url = self.format_nexus_path(path_from)
        
        try:
            self.client.download_file(url, path_to)
        except Exception as e:
            raise NhaStorageError("Download failed. Check if the remote artifact exists in the repository") from e
    
    def delete(self, hierarchy: StoreHierarchy, ignore=False):
        
        path = hierarchy.join_as_path()
        uri = os.path.join(self.repo, self.section, path)  # TODO use format_nexus_path function
        del_count = self.client.delete(uri)
        
        if del_count == 0:
            message = "Delete from Nexus failed. Check if the path exists: {}".format(uri)
            
            if ignore:
                self.LOG.warn(message)
                return False
            else:
                raise NhaStorageError(message)
        else:
            return True
    
    def get_download_cmd(self, path_from, path_to, on_board_perspective=True):
        
        if on_board_perspective:
            compass = self.compass_cls(perspective=Perspective.ON_BOARD)
        else:
            compass = self.compass
        
        curl = "curl {security} -O -u {user}:{pswd} {url}".format(
            security='' if compass.check_certificate else '--insecure',
            user=compass.user,
            pswd=compass.pswd,
            url=self.format_nexus_path(path_from)
        )
        
        move = "mkdir -p {dir} && mv {file} {path_to}".format(
            dir=os.path.dirname(path_to),
            file=os.path.basename(path_to),
            path_to=os.path.dirname(path_to)
        )
        
        return ' && '.join([curl, move])
    
    def lyst(self, path):
        
        path = self.format_nexus_path(path)
        return self.client.list(path)  # TODO: format list items in order to get only the file names


class LWWarehouse(Warehouse, ABC):
    
    conf = LazyConf(namespace=Config.Namespace.LW_WAREHOUSE)
    compass_cls = LWWarehouseCompass
    
    NO_KEYSP_EXC: Type[Exception] = None
    NO_TABLE_EXC: Type[Exception] = None

    TABLE_NAME = 'model_file'

    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        self.compass: LWWarehouseCompass = self.compass
        assert self.compass.enabled, ConfigurationError("Lightweight store is disabled")
        self.connect()
    
    @property
    def keyspace(self):
        
        return self.compass.get_store()
    
    @abstractmethod
    def create_keyspace(self):
        
        pass
    
    @abstractmethod
    def create_table(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec], *_, **__):
        
        pass
    
    def _keysp_depending_wrapper(self, func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except self.NO_KEYSP_EXC:
                self.create_keyspace()
            return func(*args, **kwargs)

        return wrapper
    
    def _table_depending_wrapper(self, func):
        
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except self.NO_TABLE_EXC:
                self.create_table(**kwargs)
            return func(*args, **kwargs)
        
        return wrapper
    
    def __getattribute__(self, attr_name):
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.KEYSP_DEP, False):
            return self._keysp_depending_wrapper(attr)
        elif getattr(attr, Flag.TABLE_DEP, False):
            return self._table_depending_wrapper(attr)
        else:
            return attr

    def lyst(self, path):
        
        raise MisusageError(
            "Lightweight store does not support models/datasets without a strict file schema definition"
        )

    def get_download_cmd(self, path_from, path_to, on_board_perspective=True):
        
        raise MisusageError(
            "Lightweight store does not support indirect deployment of models/datasets"
        )
    
    def _raise_not_found(self, hierarchy: StoreHierarchy):
        
        raise NhaStorageError(
            "Nothing found in lightweight storage with key '{key}'"
            .format(
                key=hierarchy.child
            )
        )


def keysp_dependent(func):
    
    setattr(func, Flag.KEYSP_DEP, True)
    return func


def table_dependent(func):
    
    setattr(func, Flag.TABLE_DEP, True)
    return func


class CassWarehouse(LWWarehouse):
    
    compass_cls = CassWarehouseCompass
    
    NO_KEYSP_EXC = InvalidRequest
    NO_TABLE_EXC = InvalidRequest
    
    def connect(self):
        
        self.client = Cluster(
            contact_points=self.compass.hosts,
            port=self.compass.port,
            protocol_version=4,
            load_balancing_policy=RoundRobinPolicy()
        ).connect()
        
        self.set_keyspace()
    
    @keysp_dependent
    def set_keyspace(self):
        
        self.client.set_keyspace(self.keyspace)
    
    def create_keyspace(self):
        
        stmt = """
            CREATE KEYSPACE {keysp}
            WITH REPLICATION = {{
                'class': 'SimpleStrategy',
                'replication_factor': '{repl}' 
            }}
        """.format(
            keysp=self.keyspace,
            repl=self.compass.replication
        )
        
        self.client.execute(stmt)
    
    def create_table(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec], *_, **__):

        stmt = """
            CREATE TABLE {keysp}.{table} (
                id_model VARCHAR,
                id_mover VARCHAR,
                id_file VARCHAR,
                file_content BLOB,
                PRIMARY KEY(id_model, id_mover, id_file)
            )
        """.format(
            keysp=self.keyspace,
            table=self.TABLE_NAME
        )
        
        self.client.execute(stmt)
    
    def delete(self, hierarchy: StoreHierarchy, ignore=False):

        deleted = True

        ids_stmt = """
            SELECT * FROM {keysp}.{table}
            WHERE 
                id_model='{_id_model}'
            AND id_mover='{_id_mover}'
        """.format(
            keysp=self.keyspace,
            table=self.TABLE_NAME,
            _id_model=hierarchy.parent,
            _id_mover=hierarchy.child
        )

        files = [row.id_file for row in self.client.execute(ids_stmt).current_rows]

        if len(files) == 0 and not ignore:
            self._raise_not_found(hierarchy)
        elif len(files) == 0 and ignore:
            deleted = False
        else:
            self.LOG.debug("Removing files {} from Cassandra".format(", ".join(files)))
        
        stmt = """
            DELETE FROM {keysp}.{table}
            WHERE
                id_model='{_id_model}'
            AND id_mover='{_id_mover}'
            AND id_file IN ('{_id_file}')
        """.format(
            keysp=self.keyspace,
            table=self.TABLE_NAME,
            _id_model=hierarchy.parent,
            _id_mover=hierarchy.child,
            _id_file="','".join(files) if len(files) > 1 else files[0]
        )
        
        self.client.execute(stmt)

        return deleted

    @table_dependent
    def store_files(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec]):
        
        fields = []
        values = []
        stmt = "BEGIN BATCH "
        
        for file_spec in file_schema:

            fields.append(file_spec.name)
            values.append(memoryview(file_spec.get_bytes()))

            stmt += """
                INSERT INTO {keysp}.{table} (id_model, id_mover, id_file, file_content) 
                VALUES ('{_id_model}', '{_id_mover}', '{_id_file}', %s); 
            """.format(
                keysp=self.keyspace,
                table=self.TABLE_NAME,
                _id_model=hierarchy.parent,
                _id_mover=hierarchy.child,
                _id_file=file_spec.name
            )
        stmt += " APPLY BATCH;"
        self.LOG.debug("Storing as blobs: {}".format(fields))
        self.client.execute(stmt, values)
    
    @table_dependent
    def deploy_files(self, hierarchy: StoreHierarchy, file_schema: List[FileSpec], path_to: str):

        stmt = """
            SELECT * FROM {keysp}.{table}
            WHERE 
                id_model='{_id_model}'
            AND id_mover='{_id_mover}'
        """.format(
            keysp=self.keyspace,
            table=self.TABLE_NAME,
            _id_model=hierarchy.parent,
            _id_mover=hierarchy.child
        )

        rows = self.client.execute(stmt).current_rows

        if len(rows) == 0:
            self._raise_not_found(hierarchy)

        for row in rows:
            self.LOG.debug('Deploying file: {}'.format(row.id_file))
            write_path = os.path.join(path_to, row.id_file)
            bites = row.file_content
            open(write_path, 'wb').write(bites)


def get_warehouse(lightweight=False, **kwargs) -> Warehouse:
    
    wh_compass = LWWarehouseCompass if lightweight else FSWarehouseCompass
    wh_type = wh_compass().tipe.strip().lower()
    
    cls_lookup = {
        'std': {'artif': ArtifWarehouse, 'nexus': NexusWarehouse},
        'lw': {'cass': CassWarehouse}
    }.get('lw' if lightweight else 'std')
    
    try:
        warehouse_cls = cls_lookup[wh_type]
    except KeyError:
        raise ResolutionError(
            "Could not resolve {}file manager by reference '{}'. Options are: {}"
            .format('lightweight ' if lightweight else '', wh_type, list(cls_lookup.keys()))
        )
    else:
        return warehouse_cls(**kwargs)
