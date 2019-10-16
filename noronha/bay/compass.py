# -*- coding: utf-8 -*-

"""
This module helps with configuration resolutions

Since each auxiliary service or plugin (i.e: "island") may be running in "native mode" (i.e.: in a container,
managed by the framework) or "foreign mode" (i.e.: dedicated, managed by the user), sometimes it's tricky
to decide how certain configuration parameters should be used (e.g.: Artifactory's hostname or Docker daemon's address)
"""

import logging
import os
import socket
from abc import ABC, abstractmethod
from random import randrange

from noronha.common.annotations import Configured
from noronha.common.constants import LoggerConst, DockerConst, WarehouseConst, Perspective
from noronha.common.conf import MongoConf, WarehouseConf, LoggerConf, ProjConf, DockerConf, RouterConf, CaptainConf
from noronha.common.errors import ResolutionError, ConfigurationError
from noronha.common.utils import am_i_on_board, is_it_open_sea


def find_cont_hostname():
    
    return socket.gethostname()


def find_bridge_ip():
    
    hostname = find_cont_hostname()
    own_ip = socket.gethostbyname(hostname)
    parts = own_ip.split('.')
    parts[-1] = '1'
    return '.'.join(parts)


class Compass(Configured):
    
    def __init__(self):
        
        self.conf.get('')  # triggering conf load


class DockerCompass(Compass):
    
    conf = DockerConf
    
    KEY_DAEMON_ADDRESS = 'daemon_address'
    KEY_TARGET_REGISTRY = 'registry'
    
    @property
    def daemon_address(self):
        
        return self.conf.get('daemon_address')
    
    @property
    def registry(self):
        
        return self.conf.get(self.KEY_TARGET_REGISTRY)
    
    @property
    def image_prefix(self):
        
        return self.registry or DockerConst.LOCAL_REGISTRY
    
    def get_api(self):
        
        import docker  # lazy import
        return docker.APIClient(self.daemon_address)


class CaptainCompass(Compass):
    
    conf = CaptainConf
    KEY_TYPE = 'type'
    KEY_NODES = 'nodes'
    KEY_API = 'api_key'
    KEY_TIMEOUT = 'api_timeout'
    DEFAULT_TIMEOUT = None
    
    @property
    def api_timeout(self):
        
        return self.conf.get(self.KEY_TIMEOUT, self.DEFAULT_TIMEOUT)
    
    @property
    def some_node(self):
        
        nodes = self.conf.get(self.KEY_NODES, [])
        
        if len(nodes) == 0:
            raise ConfigurationError("No node IP's configured for the container management cluster")
        else:
            return nodes[randrange(len(nodes))]
    
    @property
    def tipe(self):
        
        return self.conf[self.KEY_TYPE]
    
    @abstractmethod
    def get_namespace(self):
        
        pass
    
    @abstractmethod
    def get_resource_profile(self, section: str):
        
        pass
    
    @abstractmethod
    def get_nfs_server(self, section: str):
        
        pass
    
    @abstractmethod
    def get_stg_cls(self, section: str):
        
        pass


class SwarmCompass(CaptainCompass):
    
    DEFAULT_TIMEOUT = 20
    
    def get_namespace(self):
        
        raise NotImplementedError("Container manager 'swarm' does not apply namespace isolation")
    
    def get_resource_profile(self, section: str):
        
        raise NotImplementedError("Container manager 'swarm' does not take resource profiles")
    
    def get_nfs_server(self, section: str):
        
        raise NotImplementedError("Container manager 'swarm' does not take a NFS server")
    
    def get_stg_cls(self, section: str):
        
        raise NotImplementedError("Container manager 'swarm' does not take a storage class")


class KubeCompass(CaptainCompass):
    
    KEY_NAMESPACE = 'namespace'
    KEY_STG_CLS = 'storage_class'
    KEY_PROFILES = 'resource_profiles'
    KEY_NFS = 'nfs'
    DEFAULT_NAMESPACE = 'default'
    DEFAULT_STG_CLS = 'standard'
    DEFAULT_TIMEOUT = 60
    
    def get_namespace(self):
        
        namespace = self.conf.get(self.KEY_NAMESPACE, self.DEFAULT_NAMESPACE)
        assert isinstance(namespace, str) and len(namespace) > 0,\
            ConfigurationError("Container manager 'kube' requires an existing namespace to be configured")
        return namespace
    
    def get_stg_cls(self, section: str):
        
        stg_cls = self.conf.get(self.KEY_STG_CLS, self.DEFAULT_STG_CLS)
        assert isinstance(stg_cls, str) and len(stg_cls) > 0,\
            ConfigurationError("Container manager 'kube' requires an existing storage class to be configured")
        return stg_cls
    
    def get_resource_profile(self, section: str):
        
        prof = self.conf.get(self.KEY_PROFILES, {}).get(section)
        keys = {'limits', 'requests'}
        
        assert prof is None or (isinstance(prof, dict) and set(prof) == keys),\
            ConfigurationError("Resource profile must be a mapping with the keys {}".format(keys))
        
        return prof
    
    def get_nfs_server(self, section: str):
        
        nfs = self.conf.get(self.KEY_NFS, {})
        
        if sorted(list(nfs.keys())) == ['path', 'server']:
            pass  # a nfs server is defined for all sections
        elif section in nfs:
            nfs = nfs.get(section)  # a nfs server is defined for this specific section
        else:
            raise ConfigurationError(
                "Could not determine NFS server for section '{}' from reference: {}"
                .format(section, nfs)
            )
        
        assert isinstance(nfs, dict) and sorted(list(nfs.keys())) == ['path', 'server'],\
            ConfigurationError("NFS server must be a mapping in the form {'server': 127.0.0.1, 'path': /shared/path}")
        
        return nfs
        

class ProjectCompass(Compass):
    
    conf = ProjConf
    
    KEY_CWP = 'working_project'  # current working project
    
    @property
    def cwp(self):
        
        if am_i_on_board():
            return None  # when on board (inside managed container) project should be resolve by the image's metadata
        else:
            return self.conf.get(self.KEY_CWP)


class LoggerCompass(Compass):
    
    conf = LoggerConf
    
    KEY_LVL = 'level'
    KEY_DIR = 'directory'
    KEY_FILE_NAME = 'file_name'
    KEY_MAX_BYTES = 'max_bytes'
    KEY_BKP_COUNT = 'bkp_count'
    
    @property
    def lvl(self):
        
        lvl_alias = self.conf[self.KEY_LVL].strip().upper()
        return getattr(logging, lvl_alias)
    
    @property
    def max_bytes(self):
        
        return self.conf[self.KEY_MAX_BYTES]
    
    @property
    def bkp_count(self):
        
        return self.conf[self.KEY_BKP_COUNT]
    
    @property
    def log_file_dir(self):
        
        if am_i_on_board():
            return LoggerConst.DIR_ON_BOARD
        else:
            return self.conf.get(self.KEY_DIR, LoggerConst.DEFAULT_DIR_OFFBOARD)
    
    @property
    def log_file_name(self):
        
        if am_i_on_board():
            return '{}.{}'.format(find_cont_hostname(), LoggerConst.FILE_EXT)
        else:
            return self.conf.get(self.KEY_FILE_NAME, LoggerConst.FILE)
    
    @property
    def path_to_log_file(self):
        
        return os.path.join(self.log_file_dir, self.log_file_name)
    
    @property
    def file_handler_kwargs(self):
        
        return dict(
            filename=self.path_to_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.bkp_count
        )


class IslandCompass(ABC, Compass):
    
    alias = None
    conf = None
    
    ORIGINAL_PORT = None
    KEY_NATIVE = 'native'
    KEY_HOST = 'host'
    KEY_PORT = 'port'
    KEY_USER = 'user'
    KEY_PSWD = 'pswd'
    KEY_MAX_MB = 'disk_allocation_mb'
    KEY_SSL = 'use_ssl'
    KEY_CERT = 'check_certificate'
    DEFAULT_HOST = None
    DEFAULT_PORT = None
    DEFAULT_USER = None
    DEFAULT_PSWD = None
    DEFAULT_MAX_MB = 100*1024  # 100 GB
    
    def __init__(self, perspective=None):
        
        super().__init__()
        self.captain = CaptainCompass()
        
        if perspective is None:
            self.on_board = am_i_on_board()
        elif perspective == Perspective.ON_BOARD:
            self.on_board = True
        elif perspective == Perspective.OFF_BOARD:
            self.on_board = False
        else:
            raise ValueError("Unrecognized perspective reference: {}".format(perspective))
    
    @property
    def native(self):
        
        return self.conf.get(self.KEY_NATIVE, False)
    
    @property
    def service_name(self):
        
        return '{}-{}'.format(DockerConst.Section.ISLE, self.alias)
    
    @property
    def use_ssl(self):
        
        return self.conf.get(self.KEY_SSL, False)
    
    @property
    def check_certificate(self):
        
        default = self.use_ssl
        return self.conf.get(self.KEY_CERT, default)
    
    @property
    def protocol(self):
        
        return 'https' if self.use_ssl else 'http'
    
    @property
    def host(self):
        
        configured = self.conf.get(self.KEY_HOST, self.DEFAULT_HOST)
        
        if self.native:
            if self.captain.tipe == DockerConst.Managers.SWARM:
                if is_it_open_sea():
                    return self.service_name
                elif self.on_board:
                    return find_bridge_ip()
                else:
                    return self.DEFAULT_HOST
            elif self.captain.tipe == DockerConst.Managers.KUBE:
                if self.on_board:
                    return self.service_name
                else:
                    return self.captain.some_node
            else:
                raise ConfigurationError("Unrecognized container manager: {}".format(self.captain.tipe))
        else:
            return configured
    
    @property
    def port(self):
        
        configured = self.conf.get(self.KEY_PORT, self.DEFAULT_PORT)
        
        if self.native:
            if self.captain.tipe == DockerConst.Managers.SWARM:
                if is_it_open_sea():
                    return self.ORIGINAL_PORT
                elif self.on_board:
                    return configured
                else:
                    return configured
            elif self.captain.tipe == DockerConst.Managers.KUBE:
                if self.on_board:
                    return self.ORIGINAL_PORT
                else:
                    return configured
            else:
                raise ConfigurationError("Unrecognized container manager: {}".format(self.captain.tipe))
        else:
            return configured
    
    @property
    def user(self):
        
        if self.native and self.DEFAULT_USER is not None:
            return self.DEFAULT_USER
        else:
            return self.conf.get(self.KEY_USER)
    
    @property
    def pswd(self):
        
        if self.native and self.DEFAULT_PSWD is not None:
            return self.DEFAULT_PSWD
        else:
            return self.conf.get(self.KEY_PSWD)
    
    @property
    def max_mb(self):
        
        return self.conf.get(self.KEY_MAX_MB, self.DEFAULT_MAX_MB)


class RouterCompass(IslandCompass):
    
    alias = 'router'
    conf = RouterConf
    
    ORIGINAL_PORT = 80


class MongoCompass(IslandCompass):
    
    alias = 'mongo'
    conf = MongoConf
    
    ORIGINAL_PORT = 27017
    KEY_DB = 'database'
    KEY_CONCERN = 'write_concern'
    DEFAULT_HOST = 'localhost'
    DEFAULT_CONCERN = {'w': 1, 'j': True, 'wtimeout': 5}
    DEFAULT_MAX_MB = 1*1024  # 1 GB
    
    @property
    def db_name(self):
        
        return self.conf[self.KEY_DB]
    
    @property
    def connect_kwargs(self):
        
        return dict(
            db=self.db_name,
            alias=self.db_name,
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.pswd
        )
    
    @property
    def concern(self):
        
        if self.native:
            return self.DEFAULT_CONCERN
        else:
            return self.conf.get(self.KEY_CONCERN, self.DEFAULT_CONCERN)


class WarehouseCompass(IslandCompass):
    
    conf = WarehouseConf
    file_manager_type = None
    
    KEY_REPO = 'repository'
    DEFAULT_REPO = None
    ORIGINAL_PORT = 8081
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        assert self.conf.get('type') == self.file_manager_type,\
            ResolutionError("Current file manager type is '{}'".format(self.conf.get('type')))
    
    def get_repo(self):
        
        return self.conf.get(self.KEY_REPO, self.DEFAULT_REPO)
    
    @property
    def address(self):
        
        return '{protocol}://{host}:{port}'.format(
            protocol=self.protocol,
            host=self.host,
            port=self.port
        )


class NexusCompass(WarehouseCompass):
    
    alias = 'nexus'
    file_manager_type = WarehouseConst.Types.NEXUS
    
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_USER = 'admin'


class ArtifCompass(WarehouseCompass):
    
    alias = 'artif'
    file_manager_type = WarehouseConst.Types.ARTIF
    
    DEFAULT_HOST = 'localhost'
    DEFAULT_REPO = 'example-repo-local'
    DEFAULT_USER = 'admin'
    DEFAULT_PSWD = 'password'
     
    @property
    def auth(self):
        return self.user, self.pswd
