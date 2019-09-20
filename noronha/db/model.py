# -*- coding: utf-8 -*-

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *

from noronha.db.main import SmartDoc
from noronha.db.utils import FileDoc
from noronha.common.constants import DBConst


class ModelFile(FileDoc):
    
    pass


class DatasetFile(FileDoc):
    
    pass


class EmbeddedModel(SmartDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    model_files = EmbeddedDocumentListField(ModelFile, default=[])
    data_files = EmbeddedDocumentListField(DatasetFile, default=[])


class Model(SmartDoc, Document):
    
    _EMBEDDED_SCHEMA = EmbeddedModel
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    model_files = EmbeddedDocumentListField(ModelFile, default=[])
    data_files = EmbeddedDocumentListField(DatasetFile, default=[])
