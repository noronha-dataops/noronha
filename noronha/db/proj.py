# -*- coding: utf-8 -*-

"""Module for managing projects

A project is an entity that represents a Machine Learning project hosted by framework.
It may include one or more models and a repository to store its code.
It can be built and/or tagged as a docker image, which is mapped to a build version.
"""

from mongoengine import DENY
from mongoengine.fields import StringField, ListField, ReferenceField

from noronha.common.annotations import projected
from noronha.common.constants import DBConst, OnBoard, Flag
from noronha.common.errors import NhaAPIError
from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.model import Model


class EmbeddedProject(SmartEmbeddedDoc):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN, default='')
    home_dir = StringField(max_length=DBConst.MAX_REPO_LEN)
    git_repo = StringField(max_length=DBConst.MAX_REPO_LEN)
    docker_repo = StringField(max_length=DBConst.MAX_REPO_LEN)


class Project(SmartDoc):
    
    FILE_NAME = OnBoard.Meta.PROJ
    EMBEDDED_SCHEMA = EmbeddedProject
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN, default='')
    home_dir = StringField(max_length=DBConst.MAX_REPO_LEN)
    git_repo = StringField(max_length=DBConst.MAX_REPO_LEN)
    docker_repo = StringField(max_length=DBConst.MAX_REPO_LEN)
    models = ListField(ReferenceField(Model, reverse_delete_rule=DENY))


class Projected(object):
    
    proj: Project = None
    
    def __getattribute__(self, attr_name):
        
        attr = super().__getattribute__(attr_name)
        
        if callable(attr) and getattr(attr, Flag.PROJ, False):
            
            @projected
            def wrapper(*args, **kwargs):
                assert self.proj is not None, NhaAPIError(
                    "Cannot use method '{}' of '{}' when no working project is set"
                    .format(attr_name, self.__class__.__name__)
                )
                return attr(*args, **kwargs)
            
            return wrapper
        else:
            return attr
