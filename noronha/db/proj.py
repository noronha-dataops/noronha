# -*- coding: utf-8 -*-

"""Module for managing projects

A project is an entity that represents a Machine Learning project hosted by framework.
It may include one or more models and a repository to store its code.
It can be built and/or tagged as a docker image, which is mapped to a build version.
"""

from mongoengine import Document, EmbeddedDocument, DENY
from mongoengine.fields import StringField, ListField, ReferenceField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import SmartDoc
from noronha.db.model import Model


class EmbeddedProject(SmartDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN, default='')
    repo = StringField()


class Project(SmartDoc, Document):
    
    _FILE_NAME = OnBoard.Meta.PROJ
    _EMBEDDED_SCHEMA = EmbeddedProject
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN, default='')
    repo = StringField(required=True)
    models = ListField(ReferenceField(Model, reverse_delete_rule=DENY))
