# -*- coding: utf-8 -*-

"""Module for managing build versions

A build version is an entity that represents the event of building a Docker image,
including all metadata related to that particular build.
"""

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine import signals
from mongoengine.fields import StringField, DateTimeField, ReferenceField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import SmartDoc
from noronha.db.proj import Project


class _BuildVersion(SmartDoc):
    
    _PK_FIELDS = ['proj.name', 'tag']


class EmbeddedBuildVersion(_BuildVersion, EmbeddedDocument):
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
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
    
    @classmethod
    def pre_delete(cls, sender, document, **kwargs):
        
        from noronha.bay.shipyard import DockerTagger  # lazy import
        
        document.clean()
        DockerTagger(target_tag=document.tag, target_name=document.proj.name).untag()


signals.pre_delete.connect(BuildVersion.pre_delete, sender=BuildVersion)
