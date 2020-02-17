# -*- coding: utf-8 -*-

from mongoengine import CASCADE
from mongoengine.fields import *

from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.model import Model, EmbeddedModel
from noronha.common.constants import DBConst, OnBoard


class ProtoDataset(object):
    
    PK_FIELDS = ['model.name', 'name']


class EmbeddedDataset(SmartEmbeddedDoc):
    
    PK_FIELDS = ProtoDataset.PK_FIELDS
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    model = EmbeddedDocumentField(EmbeddedModel, default=None)
    stored = BooleanField(default=True)
    compressed = BooleanField(default=False)
    details = DictField(default={})
    lightweight = BooleanField(default=False)


class Dataset(SmartDoc, ProtoDataset):
    
    PK_FIELDS = ProtoDataset.PK_FIELDS
    FILE_NAME = OnBoard.Meta.DS
    EMBEDDED_SCHEMA = EmbeddedDataset
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    stored = BooleanField(default=True)
    compressed = BooleanField(default=False)
    details = DictField(default={})
    lightweight = BooleanField(default=False)
