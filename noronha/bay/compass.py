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

"""
This module helps with configuration resolutions

Since each auxiliary service or plugin (i.e: "island") may be running in "native mode" (i.e.: in a container,
managed by the framework) or "foreign mode" (i.e.: dedicated, managed by the user), sometimes it's tricky
to decide how certain configuration parameters should be used (e.g.: Artifactory's hostname or Docker daemon's address)
"""

import logging
import multiprocessing
import socket
from abc import ABC, abstractmethod

from noronha.common.annotations import Configured
from noronha.bay.tchest import TreasureChest
from noronha.common.utils import is_it_open_sea
from noronha.common.constants import LoggerConst, DockerConst, WarehouseConst, Perspective, Encoding, WebServerConst, OnlineConst, KubeConst
from noronha.common.conf import *
from noronha.common.errors import ResolutionError, ConfigurationError, NhaDockerError
from noronha.common.parser import resolve_log_level


def find_cont_hostname():
    
    return socket.gethostname()


def find_bridge_ip():
    
    hostname = find_cont_hostname()
    own_ip = socket.gethostbyname(hostname)
    parts = own_ip.split('.')
    parts[-1] = '1'
    return '.'.join(parts)


class Compass(Configured):
    
    conf: LazyConf = None
    
    def __init__(self, custom_conf: dict = None):
        
        self.conf.get('')  # triggering conf load
        
        if custom_conf is not None:
            self.conf = self.conf.load().as_dict().copy()
            self.conf.update(custom_conf)


class TreasureCompass(Compass):
    
    KEY_CHEST = 'tchest'
    
    def __init__(self):
        
        super().__init__()
        chest_name = self.conf.get(self.KEY_CHEST)
        
        if chest_name is None:
            self.chest = None
        else:
            self.chest = TreasureChest(chest_name)
    
    @property
    def user(self):
        
        if self.chest is None:
            return None
        else:
            return self.chest.get_user()
    
    @property
    def pswd(self):
        
        if self.chest is None:
            return None
        else:
            return self.chest.get_pswd()
    
    @property
    def token(self):
        
        if self.chest is None:
            return None
        else:
            return self.chest.get_token()


class DockerCompass(Compass):
    
    conf = DockerConf
    
    KEY_DAEMON_ADDRESS = 'daemon_address'
    KEY_TARGET_REGISTRY = 'target_registry'
    KEY_REGISTRY_SECRET = 'registry_secret'
    KEY_MOCK = 'mock_mode'
    
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
        api = docker.APIClient(self.daemon_address)
        
        try:  # dry run
            api.ping()
        except Exception as e:
            raise NhaDockerError(
                """Unable to connect to Docker daemon. """
                """Assert that the daemon is running and that your user has the required permissions."""
            ) from e
        
        return api
    
    @property
    def secret(self):
        
        return self.conf.get(self.KEY_REGISTRY_SECRET)
    
    @property
    def mock(self):
        
        return self.conf.get(self.KEY_MOCK, False)


class CaptainCompass(Compass):
    
    conf = CaptainConf
    KEY_TYPE = 'type'
    KEY_NODES = 'nodes'
    KEY_API = 'api_key'
    KEY_PROFILES = 'resource_profiles'
    KEY_TIMEOUT = 'api_timeout'
    KEY_HEALTH = 'healthcheck'
    KEYS_RESOURCES = ['limits', 'requests']
    KEY_SVC_TYPE = 'service_type'
    DEFAULT_TIMEOUT = None
    DEFAULT_HEALTHCHECK = {
        'enabled': False,
        'start_period': 60,
        'interval': 30,
        'timeout': 3,
        'retries': 3
    }
    
    @property
    def healthcheck(self):
        
        hc = self.conf.get(self.KEY_HEALTH, {})
        return join_dicts(self.DEFAULT_HEALTHCHECK, hc, allow_new_keys=False)
    
    @property
    def api_timeout(self):
        
        return self.conf.get(self.KEY_TIMEOUT, self.DEFAULT_TIMEOUT)

    def get_resource_profile(self, ref_to_profile: str):
        
        prof = self.conf.get(self.KEY_PROFILES, {}).get(ref_to_profile)

        if prof is None:
            if ref_to_profile in DockerConst.Section.ALL:
                return None
            else:
                raise ConfigurationError("Resource profile '{}' not found".format(ref_to_profile))

        prof = self.assert_profile(prof)
        
        return prof

    def assert_profile(self, profile: dict):

        assert isinstance(profile, dict), \
            ConfigurationError("Resource profile must be a dictionary, but is: {}".format(type(profile)))

        if profile.get(self.KEYS_RESOURCES[0], None) or profile.get(self.KEYS_RESOURCES[1], None):
            profile = self.assert_resources(profile)

        return profile

    def assert_resources(self, profile: dict):

        for key in self.KEYS_RESOURCES:
            for res, unit in zip(['cpu', 'memory'], ['vCores', 'MB']):
                num = profile.get(key, {}).get(res)

                if res == 'memory':
                    assert num is None or isinstance(num, int), NhaDockerError(
                        "Resource {} '{}' must be an integer ({})".format(key.rstrip('s'), res, unit))
                else:
                    assert num is None or isinstance(num, (int, float, str)), NhaDockerError(
                        "Resource {} '{}' must be integer or float or string ({})".format(key.rstrip('s'), res, unit))

                    if isinstance(num, str):
                        num = num.strip()
                        assert num[-1] == "m", NhaDockerError(
                            'When string, CPU must be in milli notation. Example: "500m"')
                        num = float(num[:-1]) / 1000
                        assert num >= 0.001, NhaDockerError("CPU precision must be at least 0.001, but was: {}"
                                                            .format(num))
                        profile[key][res] = num
                    elif isinstance(num, (int, float)):
                        assert num >= 0.001, NhaDockerError("CPU precision must be at least 0.001, but was: {}"
                                                            .format(num))
        return profile

    @property
    def tipe(self):

        return self.conf[self.KEY_TYPE]
    
    @abstractmethod
    def get_namespace(self):
        
        pass
    
    @abstractmethod
    def get_nfs_server(self):
        
        pass
    
    @abstractmethod
    def get_stg_cls(self, section: str):
        
        pass
    
    @abstractmethod
    def get_node(self) -> str:
        
        pass

    @abstractmethod
    def get_svc_type(self, resource_profile: dict) -> str:

        pass


class SwarmCompass(CaptainCompass):
    
    DEFAULT_TIMEOUT = 20
    
    def get_namespace(self):
        
        raise NotImplementedError("Container manager 'swarm' does not apply namespace isolation")
    
    def get_nfs_server(self):
        
        raise NotImplementedError("Container manager 'swarm' does not take a NFS server")
    
    def get_stg_cls(self, section: str):
        
        raise NotImplementedError("Container manager 'swarm' does not take a storage class")
    
    def get_node(self):
        
        return socket.gethostname()

    def get_svc_type(self, resource_profile: dict) -> str:

        raise NotImplementedError("Container manager 'swarm' does not take service_type configuration")


class KubeCompass(CaptainCompass):
    
    KEY_NAMESPACE = 'namespace'
    KEY_STG_CLS = 'storage_class'
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
    
    def get_nfs_server(self):
        
        nfs = self.conf.get(self.KEY_NFS, {})
        
        assert isinstance(nfs, dict) and sorted(list(nfs.keys())) == ['path', 'server'],\
            ConfigurationError("NFS server must be a mapping in the form {'server': 127.0.0.1, 'path': /shared/path}")
        
        return nfs
    
    def get_node(self):
        
        from conu import K8sBackend  # lazy import
        
        for node in K8sBackend(logging_level=logging.ERROR).core_api.list_node().items:
            for node_addr in node.status.addresses:
                if node_addr.type in ['InternalIP', 'ExternalIP']:
                    if os.system("ping -c 1 -i 0.2 -W 1 {} > /dev/null".format(node_addr.address)) == 0:
                        return node_addr.address

    def get_svc_type(self, resource_profile: dict):

        prof = resource_profile or {}

        svc_opts = {KubeConst.CLUSTER_IP.lower(): KubeConst.CLUSTER_IP,
                    KubeConst.NODE_PORT.lower(): KubeConst.NODE_PORT,
                    KubeConst.LOAD_BALANCER.lower(): KubeConst.LOAD_BALANCER}

        prof_svc = prof.get(self.KEY_SVC_TYPE, KubeConst.NODE_PORT)

        assert svc_opts.get(prof_svc.lower(), None), \
            ConfigurationError("Invalid service_type value: '{}' in resource profile definition, use one of these: {} "
                               .format(prof_svc, ",".join(KubeConst.ALL_SVC_TYPES)))

        return svc_opts[prof_svc.lower()]


def get_captain_compass():
    
    return {
        DockerConst.Managers.SWARM: SwarmCompass,
        DockerConst.Managers.KUBE: KubeCompass
    }.get(CaptainCompass().tipe)()


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
    
    KEY_NAME = 'name'
    KEY_LVL = 'level'
    KEY_DIR = 'directory'
    KEY_MAX_BYTES = 'max_bytes'
    KEY_BKP_COUNT = 'bkp_count'
    
    @property
    def name(self):
        
        return self.conf.get(self.KEY_NAME, LoggerConst.DEFAULT_NAME)
    
    @property
    def lvl(self):
        
        return resolve_log_level(self.conf[self.KEY_LVL])
    
    @property
    def max_bytes(self):
        
        return self.conf[self.KEY_MAX_BYTES]
    
    @property
    def bkp_count(self):
        
        return self.conf[self.KEY_BKP_COUNT]
    
    @property
    def log_file_dir(self):
        
        if am_i_on_board():
            return os.path.join(LoggerConst.DIR_ON_BOARD, find_cont_hostname())
        else:
            return self.conf.get(self.KEY_DIR, LoggerConst.DEFAULT_DIR_OFFBOARD)
    
    @property
    def log_file_name(self):
        
        return '{}.{}'.format(self.name, LoggerConst.FILE_EXT)
    
    @property
    def path_to_log_file(self):
        
        return os.path.join(self.log_file_dir, self.log_file_name)
    
    @property
    def file_handler_kwargs(self):
        
        return dict(
            filename=self.path_to_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.bkp_count,
            encoding=Encoding.UTF_8
        )


class IslandCompass(ABC, TreasureCompass):
    
    alias = None
    conf: LazyConf = None
    
    ORIGINAL_PORT = None
    KEY_NATIVE = 'native'
    KEY_HOST = 'host'
    KEY_PORT = 'port'
    KEY_USER = 'user'
    KEY_PSWD = 'pswd'
    KEY_MAX_MB = 'disk_allocation_mb'
    KEY_SSL = 'use_ssl'
    KEY_CERT = 'check_certificate'
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = None
    DEFAULT_USER = None
    DEFAULT_PSWD = None
    DEFAULT_MAX_MB = 100*1024  # 100 GB

    def __init__(self, perspective=None):
        
        super().__init__()
        self.captain = get_captain_compass()
        
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
                    return self.captain.get_node()
            else:
                raise NotImplementedError("Unrecognized container manager: {}".format(self.captain.tipe))
        else:
            return configured
    
    @property
    def port(self):
        
        configured = self.conf.get(self.KEY_PORT, self.DEFAULT_PORT)
        
        if self.native:
            if self.captain.tipe == DockerConst.Managers.SWARM:
                if is_it_open_sea():
                    return self.ORIGINAL_PORT
                else:
                    return configured
            elif self.captain.tipe == DockerConst.Managers.KUBE:
                if self.on_board:
                    return self.ORIGINAL_PORT
                else:
                    return configured
            else:
                raise NotImplementedError("Unrecognized container manager: {}".format(self.captain.tipe))
        else:
            return configured
    
    @property
    def user(self):
        
        if self.native and self.DEFAULT_USER is not None:
            return self.DEFAULT_USER
        else:
            return self.conf.get(self.KEY_USER) or super().user
    
    @property
    def pswd(self):
        
        if self.native and self.DEFAULT_PSWD is not None:
            return self.DEFAULT_PSWD
        else:
            return self.conf.get(self.KEY_PSWD) or super().pswd
    
    def inject_credentials(self, conf: dict):
        
        subject = conf.get(self.conf.namespace, {})
        subject.update(
            user=self.user,
            pswd=self.pswd
        )
    
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
    KEY_MAX_IDLE_TIME = 'max_idle_time_ms'
    
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
            password=self.pswd,
            maxIdleTimeMS=self.max_idle_time
        )
    
    @property
    def concern(self):
        
        if self.native:
            return self.DEFAULT_CONCERN
        else:
            return self.conf.get(self.KEY_CONCERN, self.DEFAULT_CONCERN)

    @property
    def max_idle_time(self):

        return self.conf.get(self.KEY_MAX_IDLE_TIME, None)


class WarehouseCompass(IslandCompass):
    
    KEY_TIPE = 'type'
    
    @property
    def tipe(self):
        
        return self.conf[self.KEY_TIPE]
    
    @abstractmethod
    def get_store(self):
        
        pass


class FSWarehouseCompass(WarehouseCompass):
    
    conf = FS_WarehouseConf
    file_manager_type = None
    
    KEY_REPO = 'repository'
    DEFAULT_REPO = None
    ORIGINAL_PORT = 8081
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        assert self.conf.get('type') == self.file_manager_type or self.file_manager_type is None,\
            ResolutionError(
                "Current file manager type is '{}', not '{}'"
                .format(self.conf.get('type'), self.file_manager_type)
            )
    
    def get_store(self):
        
        return self.repo
    
    @property
    def repo(self):
        
        return self.conf.get(self.KEY_REPO, self.DEFAULT_REPO)
    
    @property
    def address(self):
        
        return '{protocol}://{host}:{port}'.format(
            protocol=self.protocol,
            host=self.host,
            port=self.port
        )


class NexusCompass(FSWarehouseCompass):
    
    alias = 'nexus'
    file_manager_type = WarehouseConst.Types.NEXUS
    
    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_USER = 'admin'


class ArtifCompass(FSWarehouseCompass):
    
    alias = 'artif'
    file_manager_type = WarehouseConst.Types.ARTIF
    
    DEFAULT_REPO = 'example-repo-local'
    DEFAULT_USER = 'admin'
    DEFAULT_PSWD = 'password'


class LWWarehouseCompass(WarehouseCompass):
    
    conf = LW_WarehouseConf
    
    KEY_ENABLED = 'enabled'
    DEFAULT_ENABLED = False
    KEY_KEYSPACE = 'keyspace'
    KEY_HOST = 'hosts'
    KEY_REPLICATION = 'replication_factor'
    DEFAULT_REPLICATION = 1
    KEY_TIME_TO_LEAVE = 'time_to_leave'
    DEFAULT_TIME_TO_LEAVE = 600
    
    def get_store(self):
        
        return self.keyspace
    
    @property
    def enabled(self):
        
        return self.conf.get(self.KEY_ENABLED, self.DEFAULT_ENABLED)
    
    @property
    def keyspace(self):
        
        return self.conf[self.KEY_KEYSPACE]
    
    @property
    def hosts(self):
        
        hosts = super().host
        
        if isinstance(hosts, list):
            return hosts
        else:
            return [hosts]

    @property
    def replication(self):

        if self.native:
            return 1
        else:
            return self.conf.get(self.KEY_REPLICATION, self.DEFAULT_REPLICATION)


class CassWarehouseCompass(LWWarehouseCompass):
    
    alias = 'cass'
    file_manager_type = WarehouseConst.Types.CASS
    
    ORIGINAL_PORT = 9042
    DEFAULT_PORT = 9042


class WebAppCompass(Compass):

    conf = WebAppConf

    KEY_TYPE = 'type'
    DEFAULT_TYPE = 'flask'

    @property
    def tipe(self):
        return self.conf.get(self.KEY_TYPE, self.DEFAULT_TYPE)


class WebServerCompass(Compass):

    conf = WebServerConf

    KEY_TYPE = 'type'
    KEY_HOST = 'host'
    KEY_PORT = 'port'
    KEY_ENABLE_DEBUG = 'enable_debug'
    KEY_THREADS = 'threads'
    KEY_ENABLED = 'enabled'
    KEY_HIGH_CPU = 'high_cpu'
    KEY_NUMBER = 'number'
    KEY_EXTRA_CONF = 'extra_conf'
    DEFAULT_TYPE = 'simple'
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 8080
    DEFAULT_ENABLE_DEBUG = False
    DEFAULT_THREADS = {
        KEY_ENABLED: False,
        KEY_HIGH_CPU: False
    }
    DEFAULT_PROCESSES = 1

    @property
    def tipe(self):

        return self.conf.get(self.KEY_TYPE, self.DEFAULT_TYPE)

    @property
    def host(self):

        return self.conf.get(self.KEY_HOST, self.DEFAULT_HOST)

    @property
    def port(self):

        return self.conf.get(self.KEY_PORT, self.DEFAULT_PORT)

    @property
    def enable_debug(self):

        return self.conf.get(self.KEY_ENABLE_DEBUG, self.DEFAULT_ENABLE_DEBUG)

    @property
    def threads(self):

        threads = self.conf.get(self.KEY_THREADS, {})
        return join_dicts(self.DEFAULT_THREADS, threads, allow_overwrite=True)

    def get_threads(self):
        if self.threads[self.KEY_HIGH_CPU]:
            return int(4 * multiprocessing.cpu_count())
        else:
            return int(2 * multiprocessing.cpu_count())


class GunicornCompass(WebServerCompass):

    KEY_WORKERS = 'workers'
    KEY_WRK_CLASS = 'worker_class'
    DEFAULT_SYNC_WRK = 'sync'
    DEFAULT_THREAD_WRK = 'gthread'
    DEFAULT_MULTI_WRK = 'gevent'

    @property
    def log_level(self):

        return 'debug' if self.enable_debug else 'info'

    def get_extra_conf(self):

        extra_conf = self.conf.get(self.KEY_EXTRA_CONF, {})

        prcs = extra_conf.get(self.KEY_WORKERS, self.DEFAULT_PROCESSES)
        prcs = prcs if prcs > 0 else self.DEFAULT_PROCESSES

        if self.threads[self.KEY_ENABLED] and not self.threads.get(self.KEY_NUMBER, None):
            threads = dict(threads=self.get_threads())
        else:
            threads = self.threads.get(self.KEY_NUMBER, None)

        if prcs == 1 and self.threads[self.KEY_ENABLED]:
            worker = self.DEFAULT_THREAD_WRK
        elif prcs > 1:
            worker = extra_conf.get(self.KEY_WRK_CLASS, self.DEFAULT_MULTI_WRK)
        else:
            worker = self.DEFAULT_SYNC_WRK

        conf = dict(
            bind='{}:{}'.format(self.host, self.port),
            workers=int(prcs),
            worker_class=worker,
            loglevel=self.log_level)

        return join_dicts(conf, threads)


def get_server_compass():
    return {
        WebServerConst.Servers.SIMPLE: WebServerCompass,
        WebServerConst.Servers.GUNICORN: GunicornCompass
    }.get(WebServerCompass().tipe)()


class DeploymentCompass:

    def __init__(self, depl=None):

        from noronha.db.depl import Deployment  # avoid circular import

        self.LOCALHOST = 'localhost'
        self.ORIGINAL_PORT = OnlineConst.PORT
        self.captain_compass = get_captain_compass()
        self.on_board = am_i_on_board()
        self.open_sea = is_it_open_sea()
        self.depl = depl if depl else Deployment.load()

    @property
    def service_name(self):

        return '{}-{}-{}'.format(DockerConst.Section.DEPL, self.depl.proj.name, self.depl.name)

    @property
    def host(self):

        if self.captain_compass.tipe == DockerConst.Managers.SWARM:
            if self.open_sea:
                return self.service_name
            elif self.on_board:
                return find_bridge_ip()
            else:
                return self.LOCALHOST
        elif self.captain_compass.tipe == DockerConst.Managers.KUBE:
            if self.on_board or self.open_sea:
                return self.service_name
            else:
                return self.captain_compass.get_node()

    @property
    def port(self):

        if self.captain_compass.tipe == DockerConst.Managers.SWARM:
            if self.open_sea:
                return self.ORIGINAL_PORT
            else:
                return self.depl.host_port
        elif self.captain_compass.tipe == DockerConst.Managers.KUBE:
            if self.on_board or self.open_sea:
                return self.ORIGINAL_PORT
            else:
                return self.depl.host_port

    def get_endpoints(self) -> list:

        endpoints = []

        if self.captain_compass.tipe == DockerConst.Managers.KUBE:
            endpoints = self._get_kube_endpoints()
        elif self.captain_compass.tipe == DockerConst.Managers.SWARM:
            endpoints = self._get_swarm_endpoints()

        return ['http://{}:{}'.format(endpoint, self.port) for endpoint in endpoints]

    def _get_kube_endpoints(self):

        if self.on_board or self.open_sea:

            from conu import K8sBackend  # lazy import

            endpoints = []

            for svc in K8sBackend(logging_level=logging.ERROR).core_api.list_namespaced_endpoints(
                    self.captain_compass.get_namespace()).items:

                dyct = svc.to_dict()

                if dyct.get('metadata', {}).get('name', '') == self.service_name:

                    for address in dyct['subsets'][0]['addresses']:
                        endpoints += [address['ip']]
        else:
            endpoints = [self.host] if self.port is not None else []

        return endpoints

    def _get_swarm_endpoints(self):

        if self.open_sea:

            from conu import DockerBackend  # lazy import

            endpoints = []

            for cont in DockerBackend(logging_level=logging.ERROR).list_containers():

                details = cont.inspect()
                svc = details.get('Config', {}).get('Labels', {}).get('com.docker.swarm.service.name', '')

                if svc == self.service_name:
                    address = details.get('NetworkSettings', {}) \
                                     .get('Networks', {}) \
                                     .get(DockerConst.NETWORK, {}) \
                                     .get('IPAddress', None)

                    endpoints += [address] if address else []

        elif self.port is not None:
            endpoints = [self.host]
        else:
            # TODO use router address
            endpoints = []

        return endpoints
