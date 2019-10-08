# -*- coding: utf-8 -*-

import sys
from abc import ABC, abstractmethod
from click import confirm
from mongoengine import Document
from pyvalid import accepts
from pyvalid.validators import is_validator
from typing import Type

from noronha.common.constants import Flag
from noronha.common.errors import NhaAPIError, MisusageError, NhaValidationError


def projected(func):
    
    setattr(func, Flag.PROJ, True)
    return func


def relax(func):
    
    setattr(func, Flag.RELAXED, True)
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


class Configured(object):
    
    """A class that contains a static cofiguration in the form of a dictionary
    
    You may extend this class by overriding conf with a constant configuration dictionary.
    Otherwise, you may set conf after instantiating the class. Just don't forget that it's
    a static attribute, since a Configured class is supposed to have a static configuration.
    """
    
    conf: dict = None


class Documented(object):
    
    """A class that handles a certain type of MongoDB documents
    
    You may extend this class by overriding its doc property with a subclass of Document,
    so that any instance of this class will handle documents with that schema and colletion.
    """
    
    doc: Type[Document] = None  # a class that extends Document


class Lazy(ABC):
    
    ready = False
    
    _LAZY_PROPERTIES = []
    
    @abstractmethod
    def setup(self):
        
        pass
    
    def __getattribute__(self, attr_name):
        
        if attr_name in super().__getattribute__('_LAZY_PROPERTIES'):
            if not self.ready:
                self.setup()
                self.ready = True
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.READY, False):
            if not self.ready:
                self.setup()
                self.ready = True
        
        return attr


class Interactive(object):
    
    def __init__(self, interactive: bool = False):
        
        self.interactive = interactive
    
    def _decide(self, message, default: bool, interrupt=False):
        
        if self.interactive:
            decision = confirm(text=message)
        else:
            decision = default
        
        if interrupt and decision is False:
            sys.exit(1)
        else:
            return decision


class Projected(object):
    
    proj: Document = None  # an actual Document instance (not a Document type as in Documented)
    
    def __getattribute__(self, attr_name):
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.PROJ, False) and self.proj is None:
            raise NhaAPIError("Cannot use method '{}' of '{}' when no working project is set"
                              .format(attr_name, self.__class__.__name__))
        else:
            return attr


class Relaxed(object):
    
    relaxed: bool = True
    
    def relaxed_wrapper(self, func):
        
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                return None
        
        return wrapper
    
    def __getattribute__(self, attr_name):
        
        attr = super().__getattribute__(attr_name)
        
        if getattr(attr, Flag.RELAXED, False) and self.relaxed:
            return self.relaxed_wrapper(attr)
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
    
    def __init__(self, scope: str = None):
        
        self.scope = scope or self.Scope.DEFAULT


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
