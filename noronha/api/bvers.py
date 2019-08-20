# -*- coding: utf-8 -*-

from noronha.api.main import NoronhaAPI
from noronha.common.annotations import projected
from noronha.common.constants import DockerConst
from noronha.db.bvers import BuildVersion


class BuildVersionAPI(NoronhaAPI):
    
    doc = BuildVersion
    valid = NoronhaAPI.valid
    
    @projected
    def info(self, tag=DockerConst.LATEST):
        
        return super().info(proj=self.proj, tag=tag)
    
    @projected
    def rm(self, tag=DockerConst.LATEST):
        
        return super().rm(proj=self.proj, tag=tag)
    
    @projected
    def lyst(self, _filter: dict = None, **kwargs):
        
        kwargs['proj'] = self.proj.name
        return super().lyst(_filter=_filter, **kwargs)
