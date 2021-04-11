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

import os
from kaptan import Kaptan

from noronha.common.annotations import Lazy, ready
from noronha.common.constants import Package, Config, HostUser
from noronha.common.errors import ConfigurationError
from noronha.common.parser import join_dicts
from noronha.common.utils import am_i_on_board


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
    
    _DICT_METHODS = tuple(['get', 'update', 'keys', 'values', 'items',
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
    
    def copy(self):
        
        copied = self.__class__(
            namespace=self.namespace,
            sources=self.sources
        )
        
        copied.ready = self.ready
        
        if self.ready:
            copied.update(self)
        
        return copied
    
    @ready
    def dump(self):
        
        return Kaptan().import_config(self.as_dict()).export(handler=Config.FMT)
    
    def load(self):
        
        default_conf, user_conf, local_conf = [
            None if not os.path.exists(src)
            else Kaptan(handler=Config.FMT).import_config(src)
            for src in self.sources
        ]
        
        assert default_conf is not None,\
            ConfigurationError("Default configuration not found at {}".format(self.sources[0]))
        
        conf_opts = [local_conf, user_conf, {}]  # if local conf was found, user conf is ignored
        child_conf = filter(lambda x: x is not None, conf_opts).__next__()  # returns first non empty option
        
        super().__init__(**join_dicts(
            default_conf.get(self.namespace, {}),
            child_conf.get(self.namespace, {}),
            allow_overwrite=True
        ))
        
        return self


AllConf = LazyConf()
DockerConf = LazyConf(namespace=Config.Namespace.DOCKER)
MongoConf = LazyConf(namespace=Config.Namespace.MONGO)
FS_WarehouseConf = LazyConf(namespace=Config.Namespace.FS_WAREHOUSE)
LW_WarehouseConf = LazyConf(namespace=Config.Namespace.LW_WAREHOUSE)
RouterConf = LazyConf(namespace=Config.Namespace.ROUTER)
LoggerConf = LazyConf(namespace=Config.Namespace.LOGGER)
ProjConf = LazyConf(namespace=Config.Namespace.PROJECT)
OnlineConf = LazyConf(namespace=Config.Namespace.ONLINE)
CaptainConf = LazyConf(namespace=Config.Namespace.DOCKER_MANAGER)
WebServerConf = LazyConf(namespace=Config.Namespace.WEB_SERVER)
WebAppConf = LazyConf(namespace=Config.Namespace.WEB_APP)
