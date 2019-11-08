# -*- coding: utf-8 -*-

"""Module for defining database objects (i.e.: ORM)"""

import os
import random_name
import re
from bson import ObjectId
from datetime import datetime
from mongoengine import EmbeddedDocument, Document
from mongoengine.base import BaseList, BaseDocument
from mongoengine.connection import connect
from mongoengine.fields import StringField, ReferenceField, EmbeddedDocumentField, DateTimeField
from pymongo.write_concern import WriteConcern
from string import Template as StringTemplate
from typing import Type

from noronha.bay.compass import MongoCompass
from noronha.common.constants import DBConst, DateFmt, OnBoard
from noronha.common.errors import DBError
from noronha.common.logging import LOG


compass = MongoCompass()
connect(**compass.connect_kwargs)

DOC_META = {
    'write_concern': WriteConcern(**compass.concern),
    'db_alias': compass.db_name,
    'cascade': True,
    'allow_inheritance': True
}


class PrettyDoc(BaseDocument):
    
    _fields_ordered = []
    meta = DOC_META
    
    def as_dict(self, depth=0, pretty=False):
        
        assert depth <= DBConst.MAX_EXPAND_DEPTH
        dyct = dict([
            (key, self._expand_value(val, depth, pretty))
            for key, val in [(key, getattr(self, key)) for key in self._fields_ordered]
        ])
        
        if pretty:
            dyct.pop('id', None)
            dyct.pop('_id', None)
            dyct.pop('_cls', None)
        
        return dyct
    
    def _expand_value(self, val, depth, pretty):
        
        if isinstance(val, PrettyDoc):
            if pretty:
                return val.show()
            elif depth > 0:
                return val.as_dict(depth-1, pretty)
            else:
                return val
        elif isinstance(val, BaseList):
            return [self._expand_value(v, depth - 1, pretty) for v in val]
        elif isinstance(val, datetime):
            return val.strftime(DateFmt.READABLE)
        elif isinstance(val, ObjectId):
            return None
        else:
            return val
    
    def expanded(self):
        
        return self.as_dict(depth=DBConst.MAX_EXPAND_DEPTH)
    
    def pretty(self):
        
        return self.as_dict(depth=DBConst.MAX_EXPAND_DEPTH, pretty=True)
    
    def show(self):
        
        pretty = self.pretty()
        pretty.pop('modified', None)
        return pretty


class SmartDoc(PrettyDoc):
    
    _PK_FIELDS = ['name']  # override with a list of fields for building a composite primary key
    _FILE_NAME = None  # override with a string
    _EMBEDDED_SCHEMA = None  # override with a class that extends EmbeddedDocument
    
    _id = StringField(primary_key=True)
    modified = DateTimeField()
    
    _fields = {}
    
    def get(self, key: str, _obj=None, default=None):
        
        _obj = _obj or self
        keys = (key or '').split('.', 1)
        
        if hasattr(_obj, keys[0]):
            val = getattr(_obj, keys[0])
        else:
            return default
        
        if len(keys) == 1:
            return val
        else:
            return self.get(keys[1], val, default)
    
    def get_pk(self, delimiter: str = ':', default: str = ''):
        
        return delimiter.join([
            self.get(f) or default
            for f in self.get_pk_fields()
        ])
    
    @classmethod
    def get_pk_fields(cls):
        
        if hasattr(cls, '_PK_FIELDS'):
            pk_fields = cls._PK_FIELDS
            assert isinstance(pk_fields, list) and len(pk_fields) > 0
            return pk_fields
        
        for field in cls._fields.values():
            if field.primary_key:
                return [field.name]
        else:
            raise DBError("{} document has no primary key definition".format(cls.__class__.__name__))
    
    @classmethod
    def find(cls, _strict=False, **kwargs):
        
        objs = cls.objects(**kwargs)
        
        if _strict and len(objs) == 0:
            raise DBError.NotFound("No {}s found with query {}".format(cls.__name__, kwargs))
        else:
            return objs
    
    @classmethod
    def find_one(cls, **kwargs):
        
        objs = cls.find(_strict=True, **kwargs)
        
        if len(objs) > 1:
            raise DBError.MultipleFound("Multiple {}s found with query {}".format(cls.__name__, kwargs))
        else:
            return objs[0]
    
    @classmethod
    def find_one_or_none(cls, **kwargs):
        
        objs = cls.find(_strict=False, **kwargs)
        
        if len(objs) > 1:
            raise DBError.MultipleFound("Multiple {}s found with query {}".format(cls.__name__, kwargs))
        elif len(objs) == 1:
            return objs[0]
        else:
            return None
    
    @classmethod
    def find_by_pk(cls, pk: str):
        
        pk_parts = pk.split(':')
        pk_fields = [f.split('.', 1)[0] for f in cls.get_pk_fields()]
        
        if len(pk_parts) != len(pk_fields):
            raise DBError(
                "invalid primary key for a {}: {}. Expected format is {}"
                .format(cls.__class__.__name__, pk, ':'.join(pk_fields))
            )
        
        return cls.find_one(**dict(zip(pk_fields, pk_parts)))
    
    def to_embedded(self):
        
        schema: Type[SmartDoc] = self._EMBEDDED_SCHEMA
        
        if schema is None:
            raise NotImplementedError(
                """Document of type {} cannot be converted to an embedded format """
                """because an embedding schema hasn't been defined for its type""".format(self.__class__.__name__)
            )
        else:
            stg = dict()
            
            for key, field in schema._fields.items():
                val = getattr(self, key)
                
                if isinstance(field, EmbeddedDocumentField):
                    try:
                        stg[key] = val.to_embedded()
                    except (NotImplementedError, AttributeError):
                        stg[key] = val
                else:
                    stg[key] = val
            
            stg['_cls'] = schema.__name__
            return schema(**stg)
    
    def _basename_to_regex(self, name: str):
        
        exp = '\\.'.join([
            part or '[\\w-]*' for part  # name part or wildcard
            in name.split('.')  # pk split in parts
        ])
        
        return re.compile(r'' + exp)  # e.g.: some_model.any_ds -> some_model\.\w*
    
    def get_dir_name(self):
        
        return self.get_pk(delimiter='.')  # e.g.: some_model.some_ds
    
    def get_dir_name_regex(self):
        
        return self._basename_to_regex(self.get_dir_name())
    
    def get_file_name(self):
        
        tmpl = StringTemplate(self._FILE_NAME)
        return tmpl.safe_substitute(name=self.get_dir_name())
    
    def get_file_name_regex(self):
        
        return self._basename_to_regex(self.get_file_name())
    
    def to_file_tuple(self) -> (str, str):
        
        if self._FILE_NAME is None:
            raise NotImplementedError(
                """Document of type {} cannot be converted to a file tuple (file_name, file_content) """
                """because a file_name hasn't been defined for its type""".format(self.__class__.__name__)
            )
        else:
            return self.get_file_name(), self.to_json()
    
    @classmethod
    def load(cls, src_path=OnBoard.META_DIR, ignore=False):
        
        if os.path.isfile(src_path):
            return cls.from_json(open(src_path).read())
        elif cls._FILE_NAME is None:
            raise NotImplementedError(
                """Document of type {} cannot be loaded from a file tuple """
                """because a _FILE_NAME hasn't been defined for its type""".format(cls.__class__.__name__)
            )
        else:
            src_file = os.path.join(src_path, cls._FILE_NAME)  # will not work if file name requires pk substitution
            
            if os.path.isfile(src_file):
                return cls.from_json(open(src_file).read())
            elif ignore:
                return cls()
            else:
                raise FileNotFoundError(src_file)
    
    def clean(self):
        
        if not isinstance(self, EmbeddedDocument):
            self.modified = datetime.now()
        
        if hasattr(self, 'name') and self.name is None:
            name = random_name.generate_name(separator='-')
            setattr(self, 'name', name)
            LOG.warn("{} is anonymous. Using random name: {}".format(self.__class__.__name__, name))
        
        for key, val in self._fields.items():
            if isinstance(val, ReferenceField):
                getattr(self, key)  # assure that referenced document exists
        
        self._id = self.get_pk()
    
    def show(self):
        
        pk = self.get_pk(default='None')
        
        if issubclass(self.__class__, EmbeddedDocument):
            return ':'.join([
                pk,
                self.modified.strftime(DateFmt.READABLE)
            ])
        else:
            return pk


class Documented(object):
    
    """A class that handles a certain type of MongoDB documents
    
    You may extend this class by overriding its doc property with a subclass of Document,
    so that any instance of this class will handle documents with that schema and colletion.
    """
    
    doc: (Type[Document], Type[SmartDoc]) = None  # any class that extends SmartDoc and Document
