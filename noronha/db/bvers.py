# -*- coding: utf-8 -*-

"""Module for managing build versions

A build version is an entity that represents the event of building a Docker image,
including all metadata related to that particular build.
"""

from mongoengine import Document, EmbeddedDocument, CASCADE
from mongoengine import signals
from mongoengine.fields import StringField, DateTimeField, ReferenceField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.proj import Project


class EmbeddedBuildVersion(DocMeta, PrettyDoc, EmbeddedDocument):
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
    docker_id = StringField()
    git_version = StringField()
    built_at = DateTimeField()


class BuildVersion(DocMeta, PrettyDoc, Document):
    
    _file_name = OnBoard.Meta.BVERS  # used when a document of this type is dumped to a file
    
    _id = StringField(primary_key=True)  # hash from make_id
    
    tag = StringField(max_length=DBConst.MAX_NAME_LEN)
    proj = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)
    docker_id = StringField(required=True)
    git_version = StringField()
    built_at = DateTimeField(required=True)
    
    def _make_id(self):
        
        return dict(
            tag=self.tag,
            proj=self.proj.name
        )
    
    class EmbeddedBuildVersion(EmbeddedBuildVersion):
        
        pass
    
    @classmethod
    def pre_delete(cls, sender, document, **kwargs):
        
        from noronha.bay.shipyard import DockerTagger  # lazy import
        
        DockerTagger(target_tag=document.tag, target_name=document.proj.name).untag()


signals.pre_delete.connect(BuildVersion.pre_delete, sender=BuildVersion)
