# -*- coding: utf-8 -*-

from mongoengine import Document, CASCADE
from mongoengine.fields import *

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.main import SmartBaseDoc
from noronha.db.movers import EmbeddedModelVersion
from noronha.db.proj import Project
from noronha.db.utils import TaskDoc
from noronha.common.constants import DBConst, OnBoard


class DeplTask(TaskDoc):
    
    pass


class Deployment(SmartBaseDoc, Document):
    
    _PK_FIELDS = ['proj.name', 'name']
    _FILE_NAME = OnBoard.Meta.DEPL
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    movers = ListField(EmbeddedDocumentField(EmbeddedModelVersion, default=None))
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    tasks = DictField(EmbeddedDocumentField(DeplTask, default=DeplTask()), default={})
    details = DictField(default={})
    
    def put_task(self, task_id, catch_existing=False):
        
        if catch_existing and task_id in self.tasks:
            return self.tasks.get(task_id)
        
        task = DeplTask()
        self.tasks[task_id] = task
        self.save()
        return task
