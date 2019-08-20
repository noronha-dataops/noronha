# -*- coding: utf-8 -*-

from mongoengine import Document, CASCADE
from mongoengine.fields import *

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.movers import EmbeddedModelVersion
from noronha.db.proj import Project
from noronha.common.constants import DBConst, OnBoard


class Deployment(DocMeta, PrettyDoc, Document):
    
    _file_name = OnBoard.Meta.DEPL  # used when a document of this type is dumped to a file
    
    _id = StringField(primary_key=True)  # hash from make_id
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    movers = EmbeddedDocumentField(EmbeddedModelVersion, default=None)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    details = DictField(default={})
    
    def _make_id(self):
        
        return dict(
            name=self.name,
            proj=self.proj.name
        )
