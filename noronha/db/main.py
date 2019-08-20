# -*- coding: utf-8 -*-

"""Module for defining database objects (i.e.: ORM)"""

import os
import random_name
from bson import ObjectId
from collections import OrderedDict
from datetime import datetime
from mongoengine import Document, ReferenceField, EmbeddedDocumentField, DateTimeField
from mongoengine.base import BaseList
from mongoengine.connection import connect
from pymongo.write_concern import WriteConcern

from noronha.bay.compass import MongoCompass
from noronha.common.constants import DBConst, DateFmt, OnBoard
from noronha.common.errors import DBError
from noronha.common.logging import LOG
from noronha.common.utils import dict_to_hash

compass = MongoCompass()
connect(**compass.connect_kwargs)


class DocMeta(object):
    
    """This class contains parameters that tell MongoEngine how to behave when interacting with MongoDB
    
    You may extend this class as it is in order to easily define a Document type. Otherwise, you may extend
    the parameters mapping DocMeta.meta by adding/overriding with your own preferences.
    """
    
    meta = {
        'write_concern': WriteConcern(**compass.concern),
        'db_alias': compass.db_name,
        'cascade': True,
        'allow_inheritance': True
    }


class DocInterface(Document):
    
    def upsert(self, filter_kwargs, update_kwargs):
        
        try:
            obj = self.find_one(**filter_kwargs)
            obj.update(**update_kwargs)
            return obj
        except DBError.NotFound:
            return self.__class__(**filter_kwargs, **update_kwargs).save()
    
    def find_one_or_none(self, **kwargs):
        
        objs = self.find(_strict=False, **kwargs)
        
        if len(objs) > 1:
            raise DBError.MultipleFound("Multiple {}s found with query {}".format(self.__class__.__name__, kwargs))
        elif len(objs) == 1:
            return objs[0]
        else:
            return None
    
    def find_one(self, **kwargs):
        
        objs = self.find(_strict=True, **kwargs)
        
        if len(objs) > 1:
            raise DBError.MultipleFound("Multiple {}s found with query {}".format(self.__class__.__name__, kwargs))
        else:
            return objs[0]
    
    def find(self, _strict=False, **kwargs):
        
        objs = self.__class__.objects(**kwargs)
        
        if _strict and len(objs) == 0:
            raise DBError.NotFound("No {}s found with query {}".format(self.__class__.__name__, kwargs))
        else:
            return objs
    
    def get_pk_name(self):
        
        for field in self._fields.values():
            if field.primary_key:
                return field.name
        else:
            return None
    
    def to_file_tuple(self) -> (str, str):
        
        if not hasattr(self, '_file_name'):
            raise NotImplementedError(
                """Document of type {} cannot be converted to a file tuple (file_name, file_content) """
                """because a file_name hasn't been defined for its type""".format(self.__class__.__name__)
            )
        else:
            return self._file_name, self.to_json()
    
    def to_embedded(self):
        
        embedded_cls_name = 'Embedded{}'.format(self.__class__.__name__)
        schema = getattr(self, embedded_cls_name, None)
        
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
            
            stg['_cls'] = embedded_cls_name
            return schema(**stg)
    
    def clean(self):
        
        if hasattr(self, 'modified'):
            self.modified = datetime.now()
        
        if hasattr(self, 'name'):
            if self.name is None:
                self.name = random_name.generate_name(separator='-')
                LOG.warn("No name was provided for document of type '{}'. Using random name: {}"
                         .format(self.__class__.__name__, self.name))
        
        for key, val in self._fields.items():
            if isinstance(val, ReferenceField):
                getattr(self, key)  # assure that referenced document exists
        
        if hasattr(self, '_make_id'):
            self._id = dict_to_hash(self._make_id())  # setting composite primary key
    
    def as_dict(self, depth=0):
        
        assert depth <= DBConst.MAX_EXPAND_DEPTH
        dyct = OrderedDict([
            (key, self._format_val(val, depth))
            for key, val in [(key, getattr(self, key)) for key in self._fields_ordered]
        ])
        
        dyct.pop('_id', None)
        return dyct
    
    def _format_val(self, val, depth):
        
        if isinstance(val, BaseList):
            return [self._format_val(v, depth=depth - 1) for v in val]
        elif isinstance(val, PrettyDoc):
            return val if depth == 0 else val.as_dict(depth=depth - 1)
        elif isinstance(val, datetime):
            return val.strftime(DateFmt.READABLE)
        elif isinstance(val, ObjectId):
            return None
        else:
            return val
    
    def pretty(self):
        
        return self.expanded()
    
    def expanded(self):
        
        return self.as_dict(depth=DBConst.MAX_EXPAND_DEPTH)
    
    def load(self, src_path=OnBoard.META_DIR, ignore=False):
        
        if not hasattr(self, '_file_name'):
            raise NotImplementedError(
                """Document of type {} cannot be loaded from a file tuple """
                """because a file_name hasn't been defined for its type""".format(self.__class__.__name__)
            )
        else:
            src_file = os.path.join(src_path, self._file_name)
            
            if os.path.exists(src_file):
                return self.__class__.from_json(open(src_file).read())
            elif ignore:
                return self.__class__()
            else:
                raise FileNotFoundError(src_file)
    
    def to_json(self, expand=False, **kwargs):
        
        if expand:
            obj = self.__class__(**self.expanded())
        else:
            obj = self
        
        return Document.to_json(obj, **kwargs)


class PrettyDoc(object):
    
    _doc_interface = DocInterface
    
    _DOC_INTERFACE_METHODS = ['clean', 'as_dict', 'pretty', 'expanded', 'to_json', '_format_val', 'load', 'to_embedded',
                              'find', 'find_one', 'find_one_or_none', 'get_pk_name', 'upsert', 'to_file_tuple']
    
    modified = DateTimeField()
    
    def __getattribute__(self, attr_name):
        
        if attr_name in super().__getattribute__('_DOC_INTERFACE_METHODS'):
            def wrapper(*args, **kwargs):
                method = getattr(self._doc_interface, attr_name)
                return method(self, *args, **kwargs)
            return wrapper
        else:
            return super().__getattribute__(attr_name)
