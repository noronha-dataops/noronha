# -*- coding: utf-8 -*-

"""Module for keeping widely used constants"""

import os
import pkg_resources
import re


FW_VERSION = '1.0.1'  # framework version
FW_TAG = 'latest'  # framework tag


class NoteConst(object):
    
    """Constants related to notebook IDE and execution"""
    
    ORIGINAL_PORT = 8888
    HOST_PORT = 30088


class Encoding(object):
    
    """Common file encodings"""
    
    ASCII = 'ascii'
    ISO_8859_1 = 'ISO-8859-1'
    UTF_8 = 'UTF-8'
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


class DBConst(object):
    
    """Constants related to the database"""
    
    MAX_NAME_LEN = 30
    MAX_DESC_LEN = 300
    MAX_EXPAND_DEPTH = 5


class IslandConst(object):
    
    """Plugin-related constants"""
    
    ARTIF = 'artif'
    NEXUS = 'nexus'
    MONGO = 'mongo'
    ROUTER = 'router'
    ESSENTIAL = [ARTIF, MONGO]


class WarehouseConst(object):
    
    """Constants related to the file management system"""
    
    MAX_FILE_NAME_LEN = 30
    MAX_FILE_EXT_LEN = 10
    MAX_FILE_SIZE_MB = 2048
    
    class Types(object):
        
        """Different file manager types"""
        
        ARTIF = IslandConst.ARTIF
        NEXUS = IslandConst.NEXUS
    
    class Section(object):
        
        """Sections for prefixing file paths"""
        
        MODELS = 'models'
        NOTES = 'notebooks'
        DATASETS = 'datasets'


class EnvVar(object):
    
    """Names of environment variables"""
    
    ON_BOARD = 'AM_I_ON_BOARD'
    OPEN_SEA = 'IS_IT_OPEN_SEA'


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
    SHARED_MODEL_DIR = os.path.join(NHA_HOME, 'model')
    SHARED_DATA_DIR = os.path.join(NHA_HOME, 'data')
    META_DIR = os.path.join(NHA_HOME, 'meta')
    CONF_DIR = os.path.join(NHA_HOME, 'conf')
    LOCAL_MODEL_DIR = os.path.join('/model')
    LOCAL_DATA_DIR = os.path.join('/data')
    APP_HOME = '/app'
    LOG_DIR = '/logs'
    ENTRYPOINT = '/entrypoint.sh'
    
    class Meta(object):
        
        """Nomenclature for metadata files"""
        
        PROJ = 'proj.{}'.format(Extension.META)  # project
        BVERS = 'bvers.{}'.format(Extension.META)  # build version
        MOVERS = 'movers.{}'.format(Extension.META)  # model version
        TRAIN = 'train.{}'.format(Extension.META)  # training
        DEPL = 'depl.{}'.format(Extension.META)  # deployment
        DS = 'ds.{}'.format(Extension.META)  # dataset


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
        WAREHOUSE = 'file_manager'
        ONLINE = 'predict.online'


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
    
    NAME = 'noronha'
    FILE_EXT = Extension.LOG
    FILE = '{}.{}'.format(NAME, FILE_EXT)
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
    NHA_BASE_IMG = 'noronha.everis.ai/noronha:{}'.format(FW_TAG)
    LOCAL_REGISTRY = 'noronha'
    NETWORK = 'nha-net'
    HANG_CMD = ['tail', '-F', Paths.DEVNULL]
    MULE_CMD = HANG_CMD
    MULE_IMG = 'appropriate/curl:{}'.format(LATEST)
    STG_MOUNT = '/staging'
    
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
