# -*- coding: utf-8 -*-

"""Module for managing build versions

A build version is an entity that represents the event of building a Docker image,
including all metadata related to that particular build.
"""

from datetime import datetime
from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine import signals
from mongoengine.fields import StringField, DateTimeField, ReferenceField, EmbeddedDocumentField

from noronha.bay.compass import DockerCompass
from noronha.common.constants import DBConst, OnBoard, DockerConst
from noronha.common.logging import LOG
from noronha.db.main import SmartDoc
from noronha.db.proj import Project, EmbeddedProject


class _BuildVersion(SmartDoc):
    
    _PK_FIELDS = ['proj.name', 'tag']


class EmbeddedBuildVersion(_BuildVersion, EmbeddedDocument):
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = EmbeddedDocumentField(EmbeddedProject, default=None)
    docker_id = StringField()
    git_version = StringField()
    built_at = DateTimeField()


class BuildVersion(_BuildVersion, Document):
    
    _FILE_NAME = OnBoard.Meta.BVERS
    _EMBEDDED_SCHEMA = EmbeddedBuildVersion
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    docker_id = StringField(required=True)
    git_version = StringField()
    built_at = DateTimeField(required=True)
    built_from = StringField(required=True)
    
    @classmethod
    def pre_delete(cls, _, document, **__):
        
        document.clean()
        
        try:
            DockerCompass().get_api().remove_image(
                '{}-{}:{}'.format(
                    DockerConst.Section.PROJ,
                    document.proj.name,
                    document.tag
                )
            )
        except Exception as e:
            LOG.error(e)
            return False
        else:
            return True
    
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
