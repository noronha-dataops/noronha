# -*- coding: utf-8 -*-

from mongoengine import Document
from mongoengine.fields import *

from noronha.db.main import SmartDoc
from noronha.common.constants import DBConst


class TreasureChestDoc(SmartDoc, Document):
    
    name = StringField(max_length=DBConst.MAX_NAME_LEN)
    owner = StringField(max_length=DBConst.MAX_NAME_LEN)
    desc = StringField(max_length=DBConst.MAX_DESC_LEN)
    details = DictField(default={})
