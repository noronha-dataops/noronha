# -*- coding: utf-8 -*-

from mongoengine import CASCADE
from mongoengine.fields import *

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.main import SmartDoc
from noronha.db.movers import EmbeddedModelVersion
from noronha.db.proj import Project
from noronha.db.utils import TaskDoc
from noronha.common.constants import DBConst, OnBoard, Task


class DeplTask(TaskDoc):
    
    pass


class Deployment(SmartDoc):
    
    PK_FIELDS = ['proj.name', 'name']
    FILE_NAME = OnBoard.Meta.DEPL
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    movers = ListField(EmbeddedDocumentField(EmbeddedModelVersion, default=None))
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    tasks = DictField(EmbeddedDocumentField(DeplTask, default=DeplTask()), default={})
    details = DictField(default={})
    replicas = IntField(default=1)
    
    def put_task(self, task_id, catch_existing=False):
        
        if catch_existing and task_id in self.tasks:
            return self.tasks.get(task_id)
        
        task = DeplTask()
        self.tasks[task_id] = task
        self.save()
        return task
    
    @property
    def availability(self):
        
        avail_tasks = list(filter(
            lambda task: task.state == Task.State.FINISHED,
            self.tasks.values())
        )
        
        return round(len(avail_tasks)/self.replicas, 2)
    
    def pretty(self):
        
        dyct = super().pretty()
        dyct['availability'] = self.availability
        return dyct
