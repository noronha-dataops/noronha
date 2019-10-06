# -*- coding: utf-8 -*-

from noronha.api.main import NoronhaAPI
from noronha.bay.island import get_island
from noronha.common.constants import IslandConst


class IslandAPI(NoronhaAPI):
    
    valid = NoronhaAPI.valid
    
    def setup(self, name: str, **kwargs):
        
        return get_island(
            name,
            resource_profile=kwargs.get('resource_profile')
        ).launch(**kwargs)
    
    def get_me_started(self, **kwargs):
        
        for name in IslandConst.ESSENTIAL:
            get_island(name).launch(**kwargs)
