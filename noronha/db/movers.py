# -*- coding: utf-8 -*-

"""Documents related to MoVers (short for Model Versions)"""

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine.fields import StringField, DictField, ReferenceField, EmbeddedDocumentField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.ds import EmbeddedDataset
from noronha.db.model import Model, EmbeddedModel
from noronha.db.train import EmbeddedTraining


class EmbeddedModelVersion(DocMeta, PrettyDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    model = EmbeddedDocumentField(EmbeddedModel, default=None)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    details = DictField(default={})


class ModelVersion(DocMeta, PrettyDoc, Document):
    
    _file_name = OnBoard.Meta.MOVERS  # used when a document of this type is dumped to a file
    
    _id = StringField(primary_key=True)  # hash from make_id
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    details = DictField(default={})
    
    def _make_id(self):
        
        return dict(
            name=self.name,
            model=self.model.name
        )
    
    class EmbeddedModelVersion(EmbeddedModelVersion):
        
        pass
