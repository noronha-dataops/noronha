# -*- coding: utf-8 -*-

from noronha.api.main import NoronhaAPI
from noronha.common.annotations import validate
from noronha.common.logging import LOG
from noronha.db.model import Model


class ModelAPI(NoronhaAPI):
    
    doc = Model
    valid = NoronhaAPI.valid
    
    def info(self, name):
        
        return super().info(name=name)
    
    def rm(self, name):
        
        # TODO: find and remove model versions and datasets. Use respective API's for that purpose
        return super().rm(name=name)
    
    def lyst(self, _filter: dict = None, **kwargs):
        
        return super().lyst(_filter=_filter, **kwargs)
    
    @validate(name=valid.dns_safe, model_files=valid.list_of_dicts, data_files=valid.list_of_dicts_or_none)
    def new(self, **kwargs):
        
        return super().new(**kwargs)
    
    @validate(model_files=valid.list_of_dicts_or_none, data_files=valid.list_of_dicts_or_none)
    def update(self, name, **kwargs):
        
        if kwargs.get('model_files'):
            LOG.warn("If 'model_files' definition is changed, old model versions may become unusable")
            self._decide("Do you want to proceed?", default=True, interrupt=True)
        
        if kwargs.get('data_files'):
            LOG.warn("If 'data_files' definition is changed, old datasets may become unusable")
            self._decide("Do you want to proceed?", default=True, interrupt=True)
        
        return super().update(
            filter_kwargs=dict(name=name),
            update_kwargs=kwargs
        )
