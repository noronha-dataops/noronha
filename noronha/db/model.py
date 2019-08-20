# -*- coding: utf-8 -*-

from mongoengine import Document, EmbeddedDocument
from mongoengine.fields import *

from noronha.db.main import DocMeta, PrettyDoc
from noronha.db.utils import FileDoc
from noronha.common.constants import DBConst


class ModelFile(FileDoc):
    
    pass


class DatasetFile(FileDoc):
    
    pass


class EmbeddedModel(DocMeta, PrettyDoc, EmbeddedDocument):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    model_files = EmbeddedDocumentListField(ModelFile, default=[])
    data_files = EmbeddedDocumentListField(DatasetFile, default=[])


class Model(DocMeta, PrettyDoc, Document):
    
    name = StringField(primary_key=True, max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    model_files = EmbeddedDocumentListField(ModelFile, default=[])
    data_files = EmbeddedDocumentListField(DatasetFile, default=[])
    
    class EmbeddedModel(EmbeddedModel):
        
        pass
