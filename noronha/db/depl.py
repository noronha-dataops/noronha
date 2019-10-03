# -*- coding: utf-8 -*-

from mongoengine import Document, CASCADE
from mongoengine.fields import *

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.main import SmartDoc
from noronha.db.movers import EmbeddedModelVersion
from noronha.db.proj import Project
from noronha.common.constants import DBConst, OnBoard


class Deployment(SmartDoc, Document):
    
    _PK_FIELDS = ['proj.name', 'name']
    _FILE_NAME = OnBoard.Meta.DEPL
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    movers = ListField(EmbeddedDocumentField(EmbeddedModelVersion, default=None))
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    details = DictField(default={})
