# -*- coding: utf-8 -*-

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine.fields import *

from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.model import Model
from noronha.common.constants import DBConst, OnBoard


class EmbeddedDataset(DocMeta, PrettyDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    stored = BooleanField(default=True)
    details = DictField(default={})


class Dataset(DocMeta, PrettyDoc, Document):
    
    _file_name = OnBoard.Meta.DS  # used when a document of this type is dumped to a file
    
    _id = StringField(primary_key=True)  # hash from make_id
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    stored = BooleanField(default=True)
    details = DictField(default={})
    
    def _make_id(self):
        
        return dict(
            name=self.name,
            model=self.model.name
        )
    
    class EmbeddedDataset(EmbeddedDataset):
        
        pass
