# -*- coding: utf-8 -*-

"""Module for managing projects

A project is an entity that represents a Machine Learning project hosted by framework.
It may include one or more models and a repository to store its code.
It can be built and/or tagged as a docker image, which is mapped to a build version.
"""

from mongoengine import Document, EmbeddedDocument, DENY
from mongoengine.fields import StringField, ReferenceField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.model import Model


class EmbeddedProject(DocMeta, PrettyDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN, default='')
    repo = StringField()


class Project(DocMeta, PrettyDoc, Document):
    
    _file_name = OnBoard.Meta.PROJ  # used when a document of this type is dumped to a file
    
    name = StringField(primary_key=True, max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN, default='')
    repo = StringField(required=True)
    model = ReferenceField(Model, required=True, reverse_delete_rule=DENY)
    
    class EmbeddedProject(EmbeddedProject):
        
        pass
