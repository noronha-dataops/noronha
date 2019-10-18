# -*- coding: utf-8 -*-

import getpass

from noronha.api.main import NoronhaAPI
from noronha.bay.tchest import TreasureChest
from noronha.common.annotations import validate
from noronha.db.tchest import TreasureChestDoc


class TreasureChestAPI(NoronhaAPI):
    
    doc = TreasureChestDoc
    valid = NoronhaAPI.valid
    
    def info(self, name):
        
        return super().info(name=name)
    
    def rm(self, name):
        
        return super().rm(name=name)
    
    def lyst(self, _filter: dict = None, **kwargs):
        
        return super().lyst(_filter=_filter, **kwargs)
    
    @validate(name=valid.dns_safe, details=(dict, None))
    def new(self, name: str = None, user: str = None, pswd: str = None, **kwargs):
        
        TreasureChest(name=name).set_auth(
            user=user,
            pswd=pswd
        )
        
        return super().new(
            name=name,
            owner=getpass.getuser(),
            **kwargs
        )
    
    @validate(details=(dict, None))
    def update(self, name: str = None, user: str = None, pswd: str = None, **kwargs):
        
        TreasureChest(name=name).set_auth(
            user=user,
            pswd=pswd
        )
        
        return super().update(
            filter_kwargs=dict(name=name),
            update_kwargs=kwargs
        )
