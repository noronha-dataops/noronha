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

"""Module for keeping widely used constants"""

import os
import pkg_resources
import re


class FrameworkConst(object):
    
    FW_NAME = 'noronha-dataops'
    FW_VERSION = '1.6.8'  # framework version
    FW_TAG = 'latest'  # framework tag


class Perspective(object):
    
    ON_BOARD = 'on_board'
    OFF_BOARD = 'off_board'


class NoteConst(object):
    
    """Constants related to notebook IDE and execution"""
    
    ORIGINAL_PORT = 8888
    HOST_PORT = 30088
    START_TIMEOUT = 20


class Encoding(object):
    
    """Common file encodings"""
    
    ASCII = 'ascii'
    ISO_8859_1 = 'ISO-8859-1'
    UTF_8 = 'UTF-8'
    DEFAULT = UTF_8
    ALL = tuple([UTF_8, ASCII, ISO_8859_1])


class OnlineConst(object):
    
    """Constants related to online inference servers"""
    
    PORT = 8080  # container port that listens for inference requests
    BINDING_HOST = '0.0.0.0'
    DEFAULT_CHARSET = Encoding.UTF_8
    
    class ReturnCode(object):
        
        """Frequently used HTTP return codes"""
        
        OK = 200
        BAD_REQUEST = 400
        SERVER_ERROR = 500
        NOT_IMPLEMENTED = 501
        SERVICE_UNAVAILABLE = 503


class Messages(object):
    
    """Frequently used output messages"""
    
    OK = 'Ok'


class Flag(object):
    
    """Flags for changing a method's behaviour"""
    
    RELAXED = 'this_method_may_return_none_if_anything_goes_wrong'
    PROJ = 'this_method_assumes_that_a_working_project_is_set'
    VALIDATION = 'this_method_is_an_argument_validation'
    READY = 'the_lazy_class_must_be_ready_before_using_this_method'
    PATIENT = 'this_method_retries_until_timeout_is_exceeded'
    KEYSP_DEP = 'this_method_depends_on_the_existence_of_a_keyspace'
    TABLE_DEP = 'this_method_depends_on_the_existence_of_a_table'


class DBConst(object):
    
    """Constants related to the database"""
    
    MAX_NAME_LEN = 64
    MAX_DESC_LEN = 512
    MAX_REPO_LEN = 512
    MAX_EXPAND_DEPTH = 4
    MAX_MB_LW_FILE = 10  # max megabytes for a model or dataset file to be considered lightweight


class IslandConst(object):
    
    """Plugin-related constants"""
    
    ARTIF = 'artif'
    NEXUS = 'nexus'
    MONGO = 'mongo'
    ROUTER = 'router'
    CASS = 'cass'
    ESSENTIAL = [ARTIF, MONGO]


class WarehouseConst(object):
    
    """Constants related to the file management system"""
    
    MAX_FILE_NAME_LEN = 64
    MAX_FILE_SIZE_MB = 2048
    
    class Types(object):
        
        """Different file manager types"""
        
        ARTIF = IslandConst.ARTIF
        NEXUS = IslandConst.NEXUS
        CASS = IslandConst.CASS
    
    class Section(object):
        
        """Sections for prefixing file paths"""
        
        MODELS = 'models'
        NOTES = 'notebooks'
        DATASETS = 'datasets'


class EnvVar(object):
    
    """Names of environment variables"""
    
    ON_BOARD = 'AM_I_ON_BOARD'
    OPEN_SEA = 'IS_IT_OPEN_SEA'
    CONTAINER_PURPOSE = 'CONTAINER_PURPOSE'


class DateFmt(object):
    
    """Common datetime formats"""
    
    COMPACT = '%Y%m%d%H%M%S'
    SYSTEM = '%Y%m%d%H%M%S%f'
    READABLE = '%Y-%m-%d %H:%M:%S'
    DEFAULT = READABLE


class Extension(object):
    
    """Common file extensions"""
    
    IPYNB = 'ipynb'
    JSON = 'json'
    PY = 'py'
    YAML = 'yaml'
    LOG = 'log'
    META = 'meta'
    PDF = 'pdf'


class Regex(object):
    
    """Regular expressions"""
    
    ALPHANUM = re.compile(r'^[a-zA-Z0-9]*$')
    DNS_SPECIAL = re.compile(r'[\-\.]')
    CMD_DELIMITER = re.compile(r'\s+&&\s+|;')
    YAML_BREAK = re.compile(r'\n[^- ]')
    LINE_BREAK = re.compile(r'[\r\n]+')


class RepoConst(object):
    
    """Nomenclature conventions for repositories and related"""
    
    class ProtoPrefix(object):
        
        """Prefixes for each repository protocol"""
        
        LOCAL = 'local://'
        GIT = 'git://'
        DOCKER = 'docker://'


class Paths(object):
    
    """Paths used frequently either on board or off board"""
    
    TMP = '/tmp'
    NHA_WORK = os.path.join(TMP, '.nha_work')
    ROOT = '/'
    DEVNULL = '/dev/null'
    ETC = '/etc'
    TZ_FILE_NAME = 'localtime'
    TZ_FILE_PATH = os.path.join(ETC, TZ_FILE_NAME)


class OnBoard(object):
    
    """Paths and files inside a managed container"""
    
    NHA_HOME = '/nha'
    SHARED_DATA_DIR = os.path.join(NHA_HOME, 'data')
    SHARED_MODEL_DIR = os.path.join(NHA_HOME, 'model')
    META_DIR = os.path.join(NHA_HOME, 'meta')
    CONF_DIR = os.path.join(NHA_HOME, 'conf')
    LOCAL_DATA_DIR = os.path.join('/data')
    LOCAL_MODEL_DIR = os.path.join('/model')
    APP_HOME = '/app'
    LOG_DIR = '/logs'
    ENTRYPOINT = '/entrypoint.sh'
    
    class Meta(object):
        
        """Nomenclature for metadata files"""
        
        PROJ = 'proj.{}'.format(Extension.JSON)  # project
        BVERS = 'bvers.{}'.format(Extension.JSON)  # build version
        TRAIN = 'train.{}'.format(Extension.JSON)  # training
        DEPL = 'depl.{}'.format(Extension.JSON)  # deployment
        MV = 'mv.${{name}}.{}'.format(Extension.JSON)  # model version. to be filled with model_name.version_name
        DS = 'ds.${{name}}.{}'.format(Extension.JSON)  # dataset. to be filled with model_name.dataset_name


class Config(object):
    
    """Name conventions in configuration files and paths"""
    
    FMT = 'yaml'
    EXT = FMT
    FILE = 'nha.{}'.format(EXT)
    LOCAL = os.path.join(os.getcwd(), FILE)
    ON_BOARD = os.path.join(OnBoard.CONF_DIR, FILE)
    APP = os.path.join(OnBoard.APP_HOME, FILE)
    
    class Namespace(object):
        
        """Namespaces that may be found inside configuration files"""
        
        DOCKER = 'docker'
        DOCKER_MANAGER = 'container_manager'
        LOGGER = 'logger'
        MONGO = 'mongo'
        PROJECT = 'project'
        ROUTER = 'router'
        FS_WAREHOUSE = 'file_store'
        LW_WAREHOUSE = 'lightweight_store'
        ONLINE = 'predict.online'
        WEB_SERVER = 'web_server'
        WEB_APP = 'web_app'


class Package(object):
    
    """Paths inside the python package"""
    
    BASE = os.path.abspath(pkg_resources.resource_filename(__package__, '..'))
    SETUP = os.path.join(BASE, 'setup.py')
    RESOURCES = os.path.join(BASE, 'resources')
    CONF = os.path.join(RESOURCES, Config.FILE)
    SH = os.path.join(RESOURCES, 'sh')
    ISLE = os.path.join(RESOURCES, 'isle')  # source files for creating plugins
    TESTS = os.path.join(RESOURCES, 'tests')
    EXAMPLES = os.path.join(RESOURCES, 'examples')


class HostUser(object):
    
    """Paths inside the user home on host machines"""
    
    HOME = os.path.expanduser('~')
    NHA = os.path.join(HOME, '.nha')
    LOG_DIR = os.path.join(NHA, 'logs')
    CONF = os.path.join(NHA, Config.FILE)


class LoggerConst(object):
    
    """Constants used when logging"""
    
    DEFAULT_NAME = 'noronha'
    FILE_EXT = Extension.LOG
    DIR_ON_BOARD = OnBoard.LOG_DIR  # log directory inside a container, mapped to outside volume/mount
    DEFAULT_DIR_OFFBOARD = HostUser.LOG_DIR
    PRETTY_FMT = 'yaml'


class Task(object):
    
    """Standards for describing tasks (e.g.: a training task)"""
    
    class State(object):
        
        WAITING = 'waiting'
        RUNNING = 'running'
        FINISHED = 'finished'
        FAILED = 'failed'
        CANCELLED = 'cancelled'
        
        ALL = [WAITING, RUNNING, FINISHED, FAILED, CANCELLED]
        TMP_STATES = [WAITING, RUNNING]  # states that may change with time
        END_STATES = [FINISHED, FAILED, CANCELLED]  # states that are final


class DockerConst(object):
    
    """Docker-related nomenclature standards"""
    
    LATEST = 'latest'
    NHA_BASE_IMG = 'noronhadataops/noronha:{}'.format(FrameworkConst.FW_TAG)
    LOCAL_REGISTRY = 'noronha'
    NETWORK = 'nha-net'
    HANG_CMD = ['tail', '-F', Paths.DEVNULL]
    MULE_CMD = HANG_CMD
    MULE_IMG = 'appropriate/curl:{}'.format(LATEST)
    STG_MOUNT = '/staging'
    
    class BuildSource(object):
        
        LOCAL = 'local'
        GIT = 'git'
        PRE = 'pre-built'
        ALL = [LOCAL, GIT, PRE]
        
    class Managers(object):
        
        KUBE = 'kube'
        SWARM = 'swarm'
    
    class Section(object):
        
        """Object prefixes for each purpose"""
        
        ISLE = 'nha-isle'
        IDE = 'nha-ide'
        TRAIN = 'nha-train'
        DEPL = 'nha-depl'
        PROJ = 'nha-proj'
        ALL = [ISLE, IDE, TRAIN, DEPL, PROJ]


class KubeConst(object):

    CLUSTER_IP = 'ClusterIP'
    NODE_PORT = 'NodePort'
    LOAD_BALANCER = 'LoadBalancer'

    ALL_SVC_TYPES = [CLUSTER_IP, NODE_PORT, LOAD_BALANCER]


class WebServerConst(object):

    class Servers(object):

        GUNICORN = 'gunicorn'
        SIMPLE = 'simple'


class WebApiConst(object):

    class Methods(object):

        GET = 'GET'
        HEAD = 'HEAD'
        POST = 'POST'
        ALL = [GET, HEAD, POST]

