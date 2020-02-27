# -*- coding: utf-8 -*-

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
        
        from noronha.bay.shipyard import ImageSpec  # 2_lazy import to avoid cyclic dependency
        
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
