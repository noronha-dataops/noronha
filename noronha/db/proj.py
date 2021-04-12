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

"""Module for managing projects

A project is an entity that represents a Machine Learning project hosted by framework.
It may include one or more models and a repository to store its code.
It can be built and/or tagged as a docker image, which is mapped to a build version.
"""

from mongoengine import DENY
from mongoengine.fields import StringField, ListField, ReferenceField

from noronha.common.annotations import projected
from noronha.common.constants import DBConst, OnBoard, Flag
from noronha.common.errors import NhaAPIError, ResolutionError
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
    
    @property
    def model(self):
        
        if len(self.models) == 1:
            return self.models[0]
        else:
            raise ResolutionError(
                "Could not resolve model inside project {}. Options are: {}"
                .format(self.name, [m.name for m in self.models])
            )


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
