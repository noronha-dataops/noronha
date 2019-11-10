# -*- coding: utf-8 -*-

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine.fields import *

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.main import SmartBaseDoc
from noronha.db.proj import Project, EmbeddedProject
from noronha.db.utils import TaskDoc
from noronha.common.constants import DBConst, OnBoard


class TrainTask(TaskDoc):
    
    pass


class _Training(SmartBaseDoc):
    
    _PK_FIELDS = ['proj.name', 'name']


class EmbeddedTraining(_Training, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = EmbeddedDocumentField(EmbeddedProject, default=None)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField()
    details = DictField(default={})


class Training(_Training, Document):
    
    _FILE_NAME = OnBoard.Meta.TRAIN
    _EMBEDDED_SCHEMA = EmbeddedTraining
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    task = EmbeddedDocumentField(TrainTask, default=TrainTask())
    details = DictField(default={})
