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

from mongoengine.fields import *
from typing import List

from noronha.db.main import SmartDoc, SmartEmbeddedDoc
from noronha.db.utils import FileDoc
from noronha.common.constants import DBConst
from noronha.common.errors import NhaValidationError


class ModelFile(FileDoc):
    
    pass


class DatasetFile(FileDoc):
    
    pass


class EmbeddedModel(SmartEmbeddedDoc):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    model_files = EmbeddedDocumentListField(ModelFile, default=[])
    data_files = EmbeddedDocumentListField(DatasetFile, default=[])


class Model(SmartDoc):
    
    EMBEDDED_SCHEMA = EmbeddedModel
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    model_files = EmbeddedDocumentListField(ModelFile, default=[])
    data_files = EmbeddedDocumentListField(DatasetFile, default=[])
    
    def _assert_lightweight(self, title: str, file_schema: List[FileDoc]):
        
        assert len(file_schema) > 0, NhaValidationError(
            "{} for model {} cannot be stored in lightweight mode has no strict file schema"
            .format(title, self.name)
        )
        
        for fyle in file_schema:
            assert fyle.max_mb <= DBConst.MAX_MB_LW_FILE,\
                NhaValidationError(
                    "File '{}' for {} of model {} is allowed to be up to {} MB. "
                    .format(fyle.name, title.lower(), self.name, fyle.max_mb) +
                    "Lightweight storage accepts only files up to {} MB"
                    .format(DBConst.MAX_MB_LW_FILE)
                )
    
    def assert_datasets_can_be_lightweight(self):
        
        self._assert_lightweight(
            title='Datasets',
            file_schema=self.data_files
        )
    
    def assert_movers_can_be_lightweight(self):
        
        self._assert_lightweight(
            title='ModelVersions',
            file_schema=self.model_files
        )
