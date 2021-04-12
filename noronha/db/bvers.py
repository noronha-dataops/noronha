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

"""Module for managing build versions

A build version is an entity that represents the event of building a Docker image,
including all metadata related to that particular build.
"""

from datetime import datetime
from mongoengine import CASCADE
from mongoengine import signals
from mongoengine.fields import StringField, DateTimeField, ReferenceField, EmbeddedDocumentField

from noronha.common.constants import DBConst, OnBoard, DockerConst
from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.proj import Project, EmbeddedProject


class ProtoBuildVersion(object):
    
    PK_FIELDS = ['proj.name', 'tag']


class EmbeddedBuildVersion(SmartEmbeddedDoc):
    
    PK_FIELDS = ProtoBuildVersion.PK_FIELDS
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = EmbeddedDocumentField(EmbeddedProject, default=None)
    docker_id = StringField()
    git_version = StringField()
    built_at = DateTimeField()


class BuildVersion(SmartDoc):
    
    PK_FIELDS = ProtoBuildVersion.PK_FIELDS
    FILE_NAME = OnBoard.Meta.BVERS
    EMBEDDED_SCHEMA = EmbeddedBuildVersion
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    docker_id = StringField(required=True)
    git_version = StringField()
    built_at = DateTimeField(required=True)
    built_from = StringField(required=True)
    
    @classmethod
    def pre_delete(cls, _, document, **__):
        
        from noronha.bay.shipyard import ImageSpec  # lazy import to avoid cyclic dependency
        
        ImageSpec.from_bvers(document).untag()
        document.clean()
    
    def save(self, built_now: bool = False, **kwargs):
        
        if built_now:
            self.built_at = 'now'
        
        super().save(**kwargs)
    
    def clean(self):
        
        super().clean()
        assert self.built_from in DockerConst.BuildSource.ALL
        
        if self.built_at == 'now':
            now = datetime.now()
            self.modified = now
            self.built_at = now


signals.pre_delete.connect(BuildVersion.pre_delete, sender=BuildVersion)
