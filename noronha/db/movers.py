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
from mongoengine.fields import StringField, DictField, ReferenceField, EmbeddedDocumentField, BooleanField

from noronha.common.constants import DBConst, OnBoard
from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.ds import EmbeddedDataset
from noronha.db.model import Model, EmbeddedModel
from noronha.db.train import EmbeddedTraining


class ProtoModelVersion(object):
    
    PK_FIELDS = ['model.name', 'name']
    FILE_NAME = OnBoard.Meta.MV


class EmbeddedModelVersion(SmartEmbeddedDoc):
    
    PK_FIELDS = ProtoModelVersion.PK_FIELDS
    FILE_NAME = ProtoModelVersion.FILE_NAME
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.use_as_pretrained = False
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    model = EmbeddedDocumentField(EmbeddedModel, default=None)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    compressed = BooleanField(default=False)
    details = DictField(default={})
    pretrained = StringField(default=None)
    lightweight = BooleanField(default=False)


class ModelVersion(SmartDoc):
    
    PK_FIELDS = ProtoModelVersion.PK_FIELDS
    FILE_NAME = ProtoModelVersion.FILE_NAME
    EMBEDDED_SCHEMA = EmbeddedModelVersion
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
    
    name = StringField(required=True, max_length=DBConst.MAX_NAME_LEN)
    model = ReferenceField(Model, required=True, reverse_delete_rule=CASCADE)
    train = EmbeddedDocumentField(EmbeddedTraining, default=None)
    ds = EmbeddedDocumentField(EmbeddedDataset, default=None)
    compressed = BooleanField(default=False)
    details = DictField(default={})
    pretrained = EmbeddedDocumentField(EmbeddedModelVersion, default=None)
    lightweight = BooleanField(default=False)
    
    def to_embedded(self):
        
        emb: EmbeddedModelVersion = super().to_embedded()
        
        if isinstance(self.pretrained, EmbeddedModelVersion):
            emb.pretrained = self.pretrained.show()
        
        return emb
