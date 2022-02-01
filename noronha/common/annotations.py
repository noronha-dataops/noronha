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

import sys
import time
from abc import ABC, abstractmethod
from click import confirm
from pyvalid import accepts
from pyvalid.validators import is_validator
from typing import Type

from noronha.common.constants import Flag
from noronha.common.errors import MisusageError, NhaValidationError, PatientError


def projected(func):
    
    setattr(func, Flag.PROJ, True)
    return func


def relax(func):
    
    setattr(func, Flag.RELAXED, True)
    return func


def patient(func):
    
    setattr(func, Flag.PATIENT, True)
    return func


def validation(func):
    
    setattr(func, Flag.VALIDATION, True)
    return func


def ready(func):
    
    setattr(func, Flag.READY, True)
    return func


def validate(**kwargs):
    
    return accepts(object, **dict([
        (key, val if not getattr(val, Flag.VALIDATION, False) else wrap_validation(key, val))
        for key, val in kwargs.items()
    ]))


def retry_when_none(limit: int):

    def decorator(func):

        def wrapper(*args, **kwargs):

            attempt = 1

            while attempt <= limit:

                response = func(*args, **kwargs)

                if response:
                    return response
                else:
                    attempt += 1
                    time.sleep(attempt/2)

        return wrapper

    return decorator


class Configured(object):
    
    """A class that contains a static cofiguration in the form of a dictionary
    
    You may extend this class by overriding conf with a constant configuration dictionary.
    Otherwise, you may set conf after instantiating the class. Just don't forget that it's
    a static attribute, since a Configured class is supposed to have a static configuration.
    """
    
    conf: dict = None


class Lazy(ABC):
    
    ready = False
    
    _LAZY_PROPERTIES = []
    
    @abstractmethod
    def setup(self):
        
        pass
    
    def __getattribute__(self, attr_name):
        
        if attr_name in super().__getattribute__('_LAZY_PROPERTIES') and not self.ready:
            self.setup()
            self.ready = True
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.READY, False) and not self.ready:
            self.setup()
            self.ready = True
        
        return attr


class Interactive(object):
    
    def __init__(self, interactive: bool = False):
        
        self.interactive_mode = interactive
    
    def _decide(self, message, default: bool, interrupt=False):
        
        if self.interactive_mode:
            decision = confirm(text=message)
        else:
            decision = default
        
        if interrupt and decision is False:
            print("Aborting...")
            sys.exit(1)
        else:
            return decision


class Relaxed(object):
    
    relaxed_mode: bool = True
    
    def _relax_wrapper(self, func):
        
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return None
        
        return wrapper
    
    def __getattribute__(self, attr_name):
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.RELAXED, False) and self.relaxed_mode:
            return self._relax_wrapper(attr)
        else:
            return attr


class Patient(object):
    
    def __init__(self, timeout: int):
        
        self.timeout = timeout
    
    def _patience_wrapper(self, func):
        
        def wrapper(*args, **kwargs):
            for attempt in range(self.timeout):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt < self.timeout:
                        if attempt == 1 and isinstance(e, PatientError):
                            e.wait_callback()
                        time.sleep(1)
                    else:
                        if isinstance(e, PatientError):
                            e.raise_callback()
                        else:
                            raise e
        
        return wrapper
    
    def __getattribute__(self, attr_name):
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.PATIENT, False):
            return self._patience_wrapper(attr)
        else:
            return attr


class ScopeTable(object):
    
    def __init__(self, options: list):
        
        self.options = options
        
        for index, option in enumerate(options):
            setattr(self, option, index)
    
    def __repr__(self):
        
        return str(self.options)


class Scoped(object):
    
    class Scope(object):
        
        """{{Explain why it's necessary to define a scope for the Scoped class}}"""
        
        NONE = "{{Describe this scope}}"
        DEFAULT = NONE
        ALL = [NONE]
    
    def __init__(self, scope: str = None):
        
        self.scope = scope or self.Scope.DEFAULT
        assert self.scope in self.Scope.ALL


def wrap_validation(arg_name, func):
    
    @is_validator
    def wrapper(*args, **kwargs):
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            message = "Argument '{}' reproved on validation '{}'".format(arg_name, func.__name__)
            raise NhaValidationError(message) from e
    
    return wrapper


class Validation(object):
    
    def __init__(self):
        
        raise MisusageError("Validation use should be static. Do not instantiate it")


class Validated(object):
    
    valid: Type[Validation] = None
