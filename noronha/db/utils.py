# -*- coding: utf-8 -*-

from datetime import datetime
from mongoengine import EmbeddedDocument
from mongoengine.fields import *

from noronha.db.main import DocMeta, PrettyDoc
from noronha.common.constants import WarehouseConst, DBConst, Task


class FileDoc(DocMeta, PrettyDoc, EmbeddedDocument):
    
    name = StringField(max_length=WarehouseConst.MAX_FILE_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    required = BooleanField(default=True)
    max_mb = IntField(default=WarehouseConst.MAX_FILE_SIZE_MB)


class TaskDoc(DocMeta, PrettyDoc, EmbeddedDocument):
    
    state = StringField(default=Task.State.WAITING)
    progress = FloatField(min_value=0.0, max_value=1.0, default=0.0)
    start_time = DateTimeField()
    update_time = DateTimeField()
    
    def clean(self):
        
        if self.progress == 1:
            self.state = Task.State.FINISHED
        elif self.state == Task.State.FINISHED:
            self.progress = 1.0
        else:
            assert self.state in Task.State.ALL
        
        self.update_time = datetime.now()
        
        if self.start_time is None:
            self.start_time = self.update_time
        
        return super().clean()
