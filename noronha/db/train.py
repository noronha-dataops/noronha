# -*- coding: utf-8 -*-

# Copyright Noronha Development Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""TODO: {{module description}}
"""

from mongoengine import CASCADE
from mongoengine.fields import *
from mongoengine.queryset.base import NULLIFY

from noronha.db.bvers import EmbeddedBuildVersion
from noronha.db.ds import Dataset
from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.proj import Project, EmbeddedProject
from noronha.db.utils import TaskDoc
from noronha.common.constants import DBConst, OnBoard


class TrainTask(TaskDoc):
    
    pass


class ProtoTraining(object):
    
    PK_FIELDS = ['proj.name', 'name']


class EmbeddedTraining(SmartEmbeddedDoc):
    
    PK_FIELDS = ProtoTraining.PK_FIELDS
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = EmbeddedDocumentField(EmbeddedProject, default=None)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField()
    details = DictField(default={})


class Training(SmartDoc):
    
    PK_FIELDS = ProtoTraining.PK_FIELDS
    FILE_NAME = OnBoard.Meta.TRAIN
    EMBEDDED_SCHEMA = EmbeddedTraining
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    bvers = EmbeddedDocumentField(EmbeddedBuildVersion, default=None)
    notebook = StringField(required=True)
    task = EmbeddedDocumentField(TrainTask, default=TrainTask())
    details = DictField(default={})
    mover = ReferenceField('ModelVersion', default=None)
    ds = ReferenceField('Dataset', default=None, reverse_delete_rule=NULLIFY)
    deploy_update = BooleanField(default=False)
