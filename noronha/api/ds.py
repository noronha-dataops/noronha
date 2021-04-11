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
            LOG.info("Purging dataset '{}' from the file manager".format(ds.show()))
            file_status = 'purged' if DatasetBarrel(ds).purge(ignore=True) else 'not_found'
        else:
            LOG.info("Dataset '{}' is not stored. Skipping purge".format(ds.show()))
            file_status = 'not_stored'
        
        return dict(
            name=name,
            model=model,
            record='removed',
            files=file_status
        )
    
    def lyst(self, _filter: dict = None, model: str = None, **kwargs):
        
        if model is not None:
            kwargs['model'] = model
        
        return super().lyst(_filter=_filter, **kwargs)
    
    def _store(self, ds: Dataset, path: str = None, files: dict = None):
        
        if path or files:  # either is not None
            barrel = DatasetBarrel(ds)
            
            if barrel.schema is None:
                LOG.warn("Publishing dataset '{}' without a strict file definition".format(ds.get_pk()))
            
            if path:
                barrel.store_from_path(path)
            elif files:
                barrel.store_from_dict(files)
            else:
                raise NotImplementedError()
            
            return barrel
        else:
            LOG.warn("Dataset '{}' for model '{}' is not being stored by the framework"
                     .format(ds.name, ds.model.name))
            ds.update(stored=False)
            return None
    
    @validate(name=valid.dns_safe_or_none, files=(dict, None), details=(dict, None))
    def new(self, name: str = None, model: str = None, path: str = None, files: dict = None, skip_upload=False,
            lightweight=False, **kwargs):
        
        model = Model.find_one(name=model)
        
        if lightweight:
            model.assert_datasets_can_be_lightweight()
        
        barrel = None
        ds = super().new(
            name=name,
            model=model,
            lightweight=lightweight,
            **kwargs,
            _duplicate_filter=dict(name=name, model=model)
        )
        
        try:
            if not skip_upload:
                barrel = self._store(ds, path, files)
        except Exception as e:
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
        
        self._store(ds, path, files)
        return ds.update(stored=True)
