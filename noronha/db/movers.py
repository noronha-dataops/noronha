# -*- coding: utf-8 -*-

"""Documents related to MoVers (short for Model Versions)"""

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine.fields import StringField, DictField, ReferenceField, EmbeddedDocumentField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import SmartDoc
from noronha.db.ds import EmbeddedDataset
from noronha.db.model import Model, EmbeddedModel
from noronha.db.train import EmbeddedTraining


class _ModelVersion(SmartDoc):
    
    _PK_FIELDS = ['model.name', 'name']


class EmbeddedModelVersion(_ModelVersion, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    model = EmbeddedDocumentField(EmbeddedModel, default=None)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    details = DictField(default={})


class ModelVersion(_ModelVersion, Document):
    
    _FILE_NAME = OnBoard.Meta.MOVERS
    _EMBEDDED_SCHEMA = EmbeddedModelVersion
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    details = DictField(default={})
    pretrained = EmbeddedDocumentField(EmbeddedModelVersion, default=None)
