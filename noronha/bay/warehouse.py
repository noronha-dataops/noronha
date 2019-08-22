# -*- coding: utf-8 -*-

"""Module for handling objects in file systems

Objects handled:
- Model version files (binaries) in Artifactory or in docker volumes
- Notebook output files (pdf) in Artifactory
- Dataset packages
"""

import os
from abc import ABC, abstractmethod
from nexuscli import nexus_client
from typing import Type

from noronha.bay.compass import WarehouseCompass, ArtifCompass, NexusCompass
from noronha.bay.utils import Workpath
from noronha.common.annotations import Configured
from noronha.common.conf import LazyConf
from noronha.common.constants import Config
from noronha.common.errors import ResolutionError, NhaStorageError


class Warehouse(ABC, Configured):
    
    conf = LazyConf(namespace=Config.Namespace.WAREHOUSE)
    compass_cls: Type[WarehouseCompass] = WarehouseCompass
    
    def __init__(self, section: str):
        
        self.section = section
        self.compass: (ArtifCompass, NexusCompass) = self.compass_cls()
        self.repo = self.compass.get_repo(self.section)
        self.client = self.get_client()
        self.assert_repo_exists()
    
    @abstractmethod
    def get_client(self):
        
        pass
    
    @abstractmethod
    def assert_repo_exists(self):
        
        pass
    
    @abstractmethod
    def upload(self, path_to, path_from=None, content=None):
        
        pass
    
    @abstractmethod
    def download(self, path_from, path_to):
        
        pass
    
    @abstractmethod
    def delete(self, path_to_file):
        
        pass


class ArtifWarehouse(Warehouse):
    
    compass_cls = ArtifCompass
    
    def get_client(self):
        
        raise NotImplementedError()  # TODO
    
    def assert_repo_exists(self):
        
        raise NotImplementedError()  # TODO
    
    def format_wh_path(self, path):
        
        return os.path.join(
            self.compass.address,  # http://host:port
            self.repo,  # example-repo-local or some other pre-configured, existing repo
            self.section,  # datasets | models | notebooks
            path  # ds_name/file_name | model_name/version_name | proj_name/path/to/notebook.ipynb
        )
    
    def upload(self, path_to, path_from=None, content=None):
        
        raise NotImplementedError()  # TODO
    
    def download(self, path_from, path_to):
        
        raise NotImplementedError()  # TODO
    
    def delete(self, path_to_file):
        
        raise NotImplementedError()  # TODO


class NexusWarehouse(Warehouse):
    
    compass_cls = NexusCompass

    def format_nexus_path(self, path):
        return os.path.join(
            self.compass.address,
            'repository',
            self.repo,
            self.section,
            path
        )
    
    def get_client(self):
        
        return nexus_client.NexusClient(
            url=self.compass.address,
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
    
    def delete(self, path_to_file, ignore=False):
        
        nexus_path = os.path.join(self.repo, self.section, path_to_file)
        del_count = self.client.delete(nexus_path)
        
        if del_count == 0:
            if ignore:
                return False
            else:
                raise NhaStorageError("Delete failed. Check if the remote artifact exists in the repository")
        elif del_count == 1:
            return True
        else:
            raise NotImplementedError()


def get_warehouse(**kwargs):
    
    cls_lookup = {'artif': ArtifWarehouse, 'nexus': NexusWarehouse}
    warehouse_ref = Warehouse.conf.get('type')
    
    try:
        warehouse_cls: Type[ArtifWarehouse, NexusWarehouse] = cls_lookup[warehouse_ref.strip().lower()]
    except (KeyError, AttributeError):
        raise ResolutionError(
            "Could not resolve file manager by reference '{}'. Options are: {}"
            .format(warehouse_ref, list(cls_lookup.keys()))
        )
    else:
        return warehouse_cls(**kwargs)
