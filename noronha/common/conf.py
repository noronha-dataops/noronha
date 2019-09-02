# -*- coding: utf-8 -*-

import os
from kaptan import Kaptan

from noronha.common.annotations import Lazy, ready
from noronha.common.constants import Package, Config, HostUser
from noronha.common.errors import ConfigurationError
from noronha.common.utils import join_dicts, am_i_on_board


class ConfSource(object):
    
    PKG = Package.CONF  # default framework conf found inside the python package
    USER = HostUser.CONF  # conf stored in the user home directory on host
    LOCAL = Config.LOCAL  # local conf or project specific conf found in runtime
    CONF = Config.ON_BOARD
    APP = Config.APP
    
    SOURCES_OFF_BOARD = [PKG, USER, LOCAL]
    SOURCES_ON_BOARD = [PKG, CONF, APP]
    ALL = SOURCES_ON_BOARD if am_i_on_board() else SOURCES_OFF_BOARD


class LazyConf(Lazy, dict):
    
    _DICT_METHODS = tuple(['get', 'update', 'keys', 'values', 'items', 'copy',
                          '__repr__', '__str__', '__getitem__', '__contains__', '__iter__'])
    
    _LAZY_PROPERTIES = _DICT_METHODS
    
    def __init__(self, namespace=None, sources=None):
        
        super().__init__()
        sources = sources or ConfSource.ALL
        assert isinstance(sources, (list, tuple))
        self.sources = sources
        self.namespace = namespace
    
    def setup(self):
        
        self.load()
    
    def as_dict(self):
        
        return dict(**self)
    
    @ready
    def dump(self):
        
        return Kaptan().import_config(self.as_dict()).export(handler=Config.FMT)
    
    def load(self):
        
        confs = [
            None if not os.path.exists(src)
            else Kaptan(handler=Config.FMT).import_config(src).get(self.namespace, {}) or {}
            for src in self.sources
        ]
        
        default_conf, env_conf, local_conf = confs
        
        assert default_conf is not None,\
            ConfigurationError("Default configuration not found at {}".format(self.sources[0]))
        
        child_conf = local_conf or env_conf  # if local conf was found, env conf is ignored
        conf = join_dicts(default_conf, child_conf, allow_overwrite=True)
        super().__init__(**conf)


AllConf = LazyConf()
DockerConf = LazyConf(namespace=Config.Namespace.DOCKER)
MongoConf = LazyConf(namespace=Config.Namespace.MONGO)
WarehouseConf = LazyConf(namespace=Config.Namespace.WAREHOUSE)
RouterConf = LazyConf(namespace=Config.Namespace.ROUTER)
LoggerConf = LazyConf(namespace=Config.Namespace.LOGGER)
ProjConf = LazyConf(namespace=Config.Namespace.PROJECT)
OnlineConf = LazyConf(namespace=Config.Namespace.ONLINE)
CaptainConf = LazyConf(namespace=Config.Namespace.DOCKER_MANAGER)
