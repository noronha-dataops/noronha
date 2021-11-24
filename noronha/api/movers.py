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
from noronha.bay.barrel import MoversBarrel
from noronha.common.annotations import validate
from noronha.common.errors import NhaAPIError, DBError
from noronha.common.logging import LOG
from noronha.db.ds import Dataset
from noronha.db.model import Model
from noronha.db.movers import ModelVersion
from noronha.db.train import Training


class ModelVersionAPI(NoronhaAPI):
    
    doc = ModelVersion
    valid = NoronhaAPI.valid
    
    def info(self, name, model):
        
        return super().info(name=name, model=model)
    
    def rm(self, name, model):
        
        mv = self.doc().find_one(name=name, model=model)

        try:
            train = Training().find_one(mover=mv)
        except DBError.NotFound:  # ignore if no training was found
            pass
        else:
            train.modify(mover=None)

        # TODO: check if movers is not being used in a depl right now
        mv.delete()
        return dict(
            name=name,
            model=model,
            record='removed',
            files='purged' if MoversBarrel(mv).purge(ignore=True) else 'not_found'
        )
    
    def lyst(self, _filter: dict = None, model: str = None, train: str = None, ds: str = None, **kwargs):
        
        if model is not None:
            kwargs['model'] = Model().find_one(name=model).name
        
        _filter = _filter or {}
        
        if train is not None:
            if self.proj is None:
                raise NhaAPIError("Cannot filter by training name if no working project is set")
            else:
                train = Training.find_one(name=train, proj=self.proj.name)
                _filter['train.name'] = train.name
                _filter['train.bvers.proj.name'] = train.bvers.proj.name
        
        if ds is not None:
            if model is None:
                raise NhaAPIError("Cannot filter by dataset name if no model was specified")
            else:
                ds = Dataset.find_one(name=ds, model=model)
                _filter['ds.name'] = ds.name
                _filter['ds.model'] = ds.model.name
        
        return super().lyst(_filter=_filter, **kwargs)
    
    def _store(self, mv: ModelVersion, path: str = None):
        
        barrel = MoversBarrel(mv)
        
        if barrel.schema is None:
            LOG.warn("Publishing model version '{}' without a strict file definition".format(mv.get_pk()))
        
        barrel.store_from_path(path)
        return barrel
    
    @validate(name=valid.dns_safe_or_none, details=(dict, None))
    def new(self, name: str = None, model: str = None, train: str = None, ds: str = None, path: str = None,
            pretrained: str = None, skip_upload=False, lightweight=False, **kwargs):
        
        if path is None:
            raise NhaAPIError("Cannot publish model version if path to model files is not provided")
        
        model = Model.find_one(name=model)
        
        if lightweight:
            model.assert_movers_can_be_lightweight()
        
        if ds is not None:
            kwargs['ds'] = Dataset.find_one(name=ds, model=model).to_embedded()
        
        if train is not None:
            if self.proj is None:
                raise NhaAPIError("Cannot determine parent training if no working project is set")
            else:
                kwargs['train'] = Training.find_one(name=train, proj=self.proj.name).to_embedded()
        
        if pretrained is not None:
            kwargs['pretrained'] = ModelVersion.find_by_pk(pretrained).to_embedded()
            LOG.info("Model version used pre-trained model '{}'".format(pretrained))
        
        mv: ModelVersion = super().new(
            name=name,
            model=model,
            lightweight=lightweight,
            **kwargs,
            _duplicate_filter=dict(name=name, model=model)
        )
        
        barrel = None
        
        try:
            if not skip_upload:
                barrel = self._store(mv, path)
        except Exception as e:
            LOG.warn("Reverting creation of model version '{}'".format(mv.name))
            mv.delete()
            if barrel is not None:
                barrel.purge(ignore=True)
            raise e
        
        return mv
    
    @validate(details=(dict, None))
    def update(self, name, model, train: str = None, ds: str = None, path: str = None, **kwargs):
        
        if ds is not None:
            kwargs['ds'] = Dataset().find_one(name=ds, model=model).to_embedded()
        
        if train is not None:
            if self.proj is None:
                raise NhaAPIError("Cannot determine parent training if no working project is set")
            else:
                kwargs['train'] = Training().find_one(name=train, proj=self.proj.name).to_embedded()
        
        mv = super().update(
            filter_kwargs=dict(name=name, model=model),
            update_kwargs=kwargs
        )
        
        if path is not None:
            self._store(mv, path)
        
        return mv
