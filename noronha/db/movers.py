# -*- coding: utf-8 -*-

"""Documents related to MoVers (short for Model Versions)"""

from mongoengine import CASCADE
from mongoengine.fields import StringField, DictField, ReferenceField, EmbeddedDocumentField, BooleanField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.ds import EmbeddedDataset
from noronha.db.model import Model, EmbeddedModel
from noronha.db.train import EmbeddedTraining


class ProtoModelVersion(object):
    
    PK_FIELDS = ['model.name', 'name']
    FILE_NAME = OnBoard.Meta.MV


class EmbeddedModelVersion(SmartEmbeddedDoc):
    
    PK_FIELDS = ProtoModelVersion.PK_FIELDS
    FILE_NAME = ProtoModelVersion.FILE_NAME
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.use_as_pretrained = False
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    model = EmbeddedDocumentField(EmbeddedModel, default=None)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    compressed = BooleanField(default=False)
    details = DictField(default={})
    pretrained = StringField(default=None)


class ModelVersion(SmartDoc):
    
    PK_FIELDS = ProtoModelVersion.PK_FIELDS
    FILE_NAME = ProtoModelVersion.FILE_NAME
    EMBEDDED_SCHEMA = EmbeddedModelVersion
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.use_as_pretrained = False
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    compressed = BooleanField(default=False)
    details = DictField(default={})
    pretrained = EmbeddedDocumentField(EmbeddedModelVersion, default=None)
    
    @classmethod
    def parse_ref(cls, ref: str):
        
        parts = (ref + ':').split(':')
        pk = ':'.join(parts[:2])
        flag = bool(parts[2])
        mv = cls.find_by_pk(pk)
        
        if flag:
            mv.pretrained = True
        
        return mv
    
    def to_embedded(self):
        
        emb: EmbeddedModelVersion = super().to_embedded()
        emb.use_as_pretrained = self.use_as_pretrained
        
        if isinstance(self.pretrained, EmbeddedModelVersion):
            emb.pretrained = self.pretrained.show()
        
        return emb
