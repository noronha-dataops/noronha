# -*- coding: utf-8 -*-

from mongoengine.fields import *

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
    
    def _assert_lightweight(self, title, file_schema):
        
        assert len(file_schema) > 0, NhaValidationError(
            "{} for model {} cannot be stored in lightweight mode has no strict file schema"
            .format(title, self.name)
        )
        
        for fyle in file_schema:
            if fyle.max_mb > DBConst.MAX_MB_LW_FILE:
                return False
        else:
            return True
    
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
