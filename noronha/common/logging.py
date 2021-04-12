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

import logging
import pathlib
from datetime import datetime
from kaptan import Kaptan
from logging.handlers import RotatingFileHandler

from noronha.bay.compass import LoggerCompass
from noronha.common.annotations import Configured, Lazy, ready
from noronha.common.constants import DateFmt, LoggerConst
from noronha.common.parser import assert_json, assert_str, StructCleaner, order_yaml, resolve_log_level


class Logger(Configured, Lazy):
    
    _LOGGER_METHODS = tuple(['debug', 'info', 'warn', 'warning', 'error'])
    
    _LAZY_PROPERTIES = ['level', 'debug_mode', 'path', 'pretty', 'background']
    
    _TAG_PER_METHOD = {
        'debug': 'DEBUG',
        'info': 'INFO',
        'warning': 'WARN',
        'error': 'ERROR'
    }
    
    _LEVEL_PER_METHOD = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARN,
        'error': logging.ERROR,
    }
    
    def __init__(self, name: str = LoggerConst.DEFAULT_NAME, **kwargs):
        
        self._logger = None
        self.name = name
        self.path = None
        self.pretty = False
        self.background = False
        self.file_handle = None
        self.cleaner = StructCleaner(depth=3)
        self.kwargs = kwargs
        self.kwargs['name'] = self.name
    
    def __getattribute__(self, attr_name):
        
        if attr_name in super().__getattribute__('_LOGGER_METHODS'):
            return self.wrap_logger(attr_name)
        else:
            return super().__getattribute__(attr_name)
    
    def setup(self):
        
        if self._logger is not None:
            return self
        
        self._logger = logging.getLogger(self.name)
        
        if len(self._logger.handlers) > 0:
            return self
        
        compass = LoggerCompass(custom_conf=self.kwargs)
        pathlib.Path(compass.log_file_dir).mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(**compass.file_handler_kwargs)
        handler.setLevel(compass.lvl)
        
        self._logger.setLevel(compass.lvl)
        self._logger.addHandler(handler)
        self._logger.propagate = False
        self.pretty = compass.conf.get('pretty', False)
        self.background = compass.conf.get('background', False)
        self.path = compass.path_to_log_file
        self.file_handle = open(self.path, 'a')
        
        if compass.conf.get('join_root') and self.name == LoggerConst.DEFAULT_NAME:
            logging.getLogger('root').addHandler(handler)
        
        return self
    
    @property
    def debug_mode(self):
        
        return self.level == logging.DEBUG
    
    @debug_mode.setter
    def debug_mode(self, debug_mode: bool):
        
        if debug_mode:
            self.set_level(logging.DEBUG)
        elif self.debug_mode:
            self.set_level(logging.INFO)
    
    @property
    def level(self):
        
        return self._logger.level
    
    @level.setter
    def level(self, level: str):
        
        self.set_level(level)
    
    @ready
    def set_level(self, level: (str, int)):
        
        self._logger.setLevel(resolve_log_level(level))
    
    def wrap_logger(self, log_method):
        
        if log_method == 'warn':
            log_method = 'warning'  # warn is deprecated in Logger module
        
        def wrapper(*args, **kwargs):
            self.log(*args, **kwargs, method=log_method)
        
        return wrapper
    
    @ready
    def log(self, msg, method, force_pretty=False, force_print=False, use_tag=True, tag=None):
        
        lvl = self._LEVEL_PER_METHOD[method]
        tag = (tag or self._TAG_PER_METHOD[method]) if use_tag else None
        msg = self.format(msg, force_pretty=force_pretty, tag=tag)
        getattr(self._logger, method)(msg)
        
        if (lvl >= self._logger.level or force_print) and not self.background:
            print(msg)
    
    def echo(self, msg):
        
        self.log(msg, method='info', force_pretty=True, force_print=True, use_tag=False)
    
    def profile(self, msg):
        
        self.log(msg, method='debug', force_pretty=True, use_tag=True, tag='PROFILE')
    
    def format(self, msg, force_pretty=False, tag=None):
        
        if not self.pretty and not force_pretty:
            return msg
        elif isinstance(msg, (list, tuple)):
            return assert_json(msg, indent=4)
        elif hasattr(msg, 'pretty'):
            msg = getattr(msg, 'pretty')()
        
        if isinstance(msg, dict):
            clean_dyct = self.cleaner(msg)
            kaptan = Kaptan().import_config(clean_dyct)
            yaml = kaptan.export(handler=LoggerConst.PRETTY_FMT, explicit_start=True)
            return order_yaml(yaml)
        
        msg = assert_str(msg, allow_none=True)
        
        if tag is None:
            return msg
        else:
            return '{ts} - {tag} - {msg}'.format(
                ts=datetime.now().strftime(DateFmt.READABLE),
                tag=tag,
                msg=msg
            )


LOG = Logger()


class LoggerHub(object):
    
    kwargs = {}
    
    hub = {
        LoggerConst.DEFAULT_NAME: LOG
    }
    
    @classmethod
    def get_logger(cls, name: str = LoggerConst.DEFAULT_NAME):
        
        return cls.hub.get(name) or cls.make_logger(name)
    
    @classmethod
    def make_logger(cls, name: str):
        
        assert name not in cls.hub
        logger = Logger(name=name, **cls.kwargs)
        cls.hub[name] = logger
        return logger
    
    @classmethod
    def configure(cls, param, value):
        
        assert param not in cls.kwargs
        assert hasattr(LOG, param)
        cls.kwargs[param] = value
        
        for logger in cls.hub.values():
            logger.kwargs[param] = value
            setattr(logger, param, value)


class Logged(object):
    
    def __init__(self, log: Logger = None):
        
        assert log is None or isinstance(log, Logger)
        self.LOG = log or LOG
    
    def set_logger(self, name):
        
        self.LOG = LoggerHub.get_logger(name=name)
    
    def reset_logger(self):
        
        self.LOG = LOG
