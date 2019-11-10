# -*- coding: utf-8 -*-

from mongoengine import CASCADE
from mongoengine.fields import *

from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.model import Model, EmbeddedModel
from noronha.common.constants import DBConst, OnBoard


class ProtoDataset(object):
    
    _PK_FIELDS = ['model.name', 'name']


class EmbeddedDataset(SmartEmbeddedDoc, ProtoDataset):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    model = EmbeddedDocumentField(EmbeddedModel, default=None)
    stored = BooleanField(default=True)
    compressed = BooleanField(default=False)
    details = DictField(default={})


class Dataset(SmartDoc, ProtoDataset):
    
    _FILE_NAME = OnBoard.Meta.DS
    _EMBEDDED_SCHEMA = EmbeddedDataset
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    stored = BooleanField(default=True)
    compressed = BooleanField(default=False)
    details = DictField(default={})
