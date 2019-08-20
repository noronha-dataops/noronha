# -*- coding: utf-8 -*-

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine.fields import *

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.proj import Project, EmbeddedProject
from noronha.db.utils import TaskDoc
from noronha.common.constants import DBConst, OnBoard


class TrainTask(TaskDoc):
    
    pass


class EmbeddedTraining(DocMeta, PrettyDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = EmbeddedDocumentField(EmbeddedProject, default=None)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField()
    details = DictField(default={})


class Training(DocMeta, PrettyDoc, Document):
    
    _file_name = OnBoard.Meta.TRAIN  # used when a document of this type is dumped to a file
    
    _id = StringField(primary_key=True)  # hash from make_id
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    task = EmbeddedDocumentField(TrainTask, default=TrainTask())
    details = DictField(default={})
    
    def _make_id(self):
        
        return dict(
            name=self.name,
            proj=self.proj.name
        )
    
    class EmbeddedTraining(EmbeddedTraining):
        
        pass
