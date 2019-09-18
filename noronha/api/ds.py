# -*- coding: utf-8 -*-

from noronha.api.main import NoronhaAPI
from noronha.bay.barrel import DatasetBarrel
from noronha.common.annotations import validate
from noronha.common.logging import LOG
from noronha.db.ds import Dataset
from noronha.db.model import Model


class DatasetAPI(NoronhaAPI):
    
    doc = Dataset
    valid = NoronhaAPI.valid
    
    def info(self, name, model):
        
        return super().info(name=name, model=model)
    
    def rm(self, name, model):
        
        ds = self.doc().find_one(name=name, model=model)
        # TODO: check if dataset is not being used in a training right now
        ds.delete()
        
        if ds.stored:
            LOG.info("Purging dataset '{}' from the file manager".format(ds.name))
            file_status = DatasetBarrel(ds).purge(ignore=True)
        else:
            LOG.info("Dataset '{}' is not stored. Skipping purge".format(ds.name))
            file_status = 'not_stored'
        
        return dict(record='removed', files=file_status, name=name, model=model)
    
    def lyst(self, _filter: dict = None, model: str = None, **kwargs):
        
        if model is not None:
            kwargs['model'] = model
        
        return super().lyst(_filter=_filter, **kwargs)
    
    @validate(name=valid.dns_safe_or_none, files=(dict, None), details=(dict, None))
    def new(self, name: str = None, model: str = None, path: str = None, files: dict = None, **kwargs):
        
        model = Model().find_one(name=model)
        barrel = None
        ds = super().new(
            name=name,
            model=model,
            **kwargs,
            _duplicate_filter=dict(name=name, model=model)
        )
        
        try:
            barrel = DatasetBarrel(ds)
            
            if path is not None:
                barrel.store_from_path(path)
            elif files is not None:
                barrel.store_from_dict(files)
            else:
                LOG.warn("Dataset '{}' for model '{}' is not being stored by the framework"
                         .format(ds.name, ds.model.name))
                ds.update(stored=False)
        except Exception as e:
            LOG.error(e)
            LOG.warn("Reverting creation of dataset '{}'".format(ds.name))
            ds.delete()
            if barrel is not None:
                barrel.purge(ignore=True)
            raise e
        else:
            return ds
    
    @validate(files=(dict, None), details=(dict, None))
    def update(self, name, model, path: str = None, files: dict = None, **kwargs):
        
        ds = super().update(
            filter_kwargs=dict(name=name, model=model),
            update_kwargs=kwargs
        )
        
        barrel = DatasetBarrel(ds)
        
        if path is not None:
            barrel.store_from_path(path)
        elif files is not None:
            barrel.store_from_dict(files)
        else:
            return ds
        
        return ds.update(stored=True)
