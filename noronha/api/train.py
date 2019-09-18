# -*- coding: utf-8 -*-

import json

from noronha.api.main import NoronhaAPI
from noronha.bay.cargo import DatasetCargo, MetaCargo, ConfCargo, LogsCargo, SharedCargo, MoversCargo
from noronha.bay.expedition import ShortExpedition
from noronha.common.annotations import validate, projected
from noronha.common.constants import DockerConst, Extension, OnBoard, Task
from noronha.common.errors import NhaAPIError
from noronha.common.logging import LOG
from noronha.common.utils import assert_extension, join_dicts
from noronha.db.bvers import BuildVersion
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.train import Training


class TrainingAPI(NoronhaAPI):
    
    doc = Training
    valid = NoronhaAPI.valid
    
    @projected
    def info(self, name):
        
        return super().info(name=name, proj=self.proj.name)
    
    @projected
    def rm(self, name):
        
        # TODO: check if training is not running
        return super().rm(name=name, proj=self.proj.name)
    
    def lyst(self, _filter: dict = None, **kwargs):
        
        if self.proj is not None:
            kwargs['proj'] = self.proj.name
        
        return super().lyst(_filter=_filter, **kwargs)
    
    @projected
    @validate(
        name=valid.dns_safe_or_none,
        details=(dict, None),
        env_vars=dict,
        mounts=list,
        params=(dict, None)
    )
    def new(self, name: str = None, tag=DockerConst.LATEST, notebook: str = None, details: dict = None,
            params: dict = None, ds: str = None, model: str = None, _replace: bool = None, pretrained: str = None,
            **kwargs):
        
        if ds is not None:
            if model is None:
                raise NhaAPIError("Cannot determine training dataset if parent model is not specified")
            
            ds = Dataset().find_one(name=ds, model=model)
            name = name or ds.name  # letting training name default to dataset name, if not specified
            assert ds.stored, NhaAPIError(
                """Dataset '{}' is not stored by the framework, so it cannot be mounted in the training container"""
                .format(ds.name)
            )
        
        bv = BuildVersion().find_one_or_none(tag=tag, proj=self.proj)
        
        if pretrained is not None:
            mv = ModelVersion.from_reference(pretrained)
            LOG.info("Pre-trained model version '{}' will be available in this training".format(pretrained))
        else:
            mv = None
        
        train: Training = super().new(
            name=name,
            proj=self.proj,
            bvers=None if bv is None else bv.to_embedded(),
            notebook=assert_extension(notebook, Extension.IPYNB),
            details=join_dicts(details or {}, dict(params=params or {}), allow_overwrite=False),
            _duplicate_filter=dict(name=name, proj=self.proj)
        )
        
        TrainingExp(train, ds, mv, tag).launch(**kwargs)
        return train.reload()


class TrainingExp(ShortExpedition):
    
    section = DockerConst.Section.TRAIN
    
    def __init__(self, train: Training, ds: Dataset = None, mv: ModelVersion = None, tag=DockerConst.LATEST):
        
        self.train = train
        self.ds = ds
        self.mv = mv
        super().__init__(proj=train.proj, tag=tag)
    
    def close(self):
        
        try:
            super().close()
            
            if self.captain.interrupted:
                LOG.warn('Failing training due to an interruption')
                self.train.reload()
                self.train.task.state = Task.State.FAILED
                self.train.save()

        except Exception:
            LOG.error("Failed to close training '{}'".format(self.make_alias()))
    
    def make_alias(self):
        
        return '{}-{}'.format(self.proj.name, self.train.name)
    
    def make_cmd(self):
        
        return [
            OnBoard.ENTRYPOINT,
            '--notebook-path',
            self.train.notebook,
            '--params',
            json.dumps(self.train.details['params'])
        ] + (['--debug'] if LOG.debug_mode else [])
    
    def make_vols(self):
        
        cargos = []
        docs = [self.proj, self.train]
        suffix = '{}-{}'.format(self.proj.name, self.train.name)
        
        if self.bvers is not None:
            docs.append(self.bvers)
        
        if self.ds is not None:
            docs.append(self.ds)
            cargos.append(DatasetCargo(self.ds))
        
        if self.mv is not None:
            docs.append(self.mv)
            cargos.append(MoversCargo(self.mv, pretrained=True))
        
        cargos += [
            MetaCargo(suffix=suffix, docs=docs),
            ConfCargo(suffix=suffix),
            MoversCargo(self.mv)
        ]
        
        return [
            LogsCargo(suffix=suffix),
            SharedCargo(suffix, cargos)
        ]
