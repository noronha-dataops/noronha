# -*- coding: utf-8 -*-

import json

from noronha.api.main import NoronhaAPI
from noronha.bay.expedition import ShortExpedition
from noronha.common.annotations import validate, projected
from noronha.common.constants import DockerConst, Extension, OnBoard, Task
from noronha.common.utils import assert_extension, join_dicts
from noronha.db.bvers import BuildVersion
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.train import Training


class TrainingAPI(NoronhaAPI):
    
    doc = Training
    valid = NoronhaAPI.valid
    
    def set_logger(self, name):
        
        super().set_logger(
            name='-'.join([
                DockerConst.Section.TRAIN,
                self.proj.name,
                name
            ])
        )
    
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
    def new(self, name: str = None, tag=DockerConst.LATEST, notebook: str = None, params: dict = None,
            details: dict = None, datasets: list = None, movers: list = None, _replace: bool = None,
            **kwargs):
        
        self.set_logger(name)
        bv = BuildVersion.find_one_or_none(tag=tag, proj=self.proj)
        movers = [ModelVersion.find_by_pk(mv).to_embedded() for mv in movers or []]
        datasets = [Dataset.find_by_pk(ds) for ds in datasets or []]
        
        if name is None:
            all_names = set([ds.name for ds in datasets])
            
            if len(all_names) == 1:
                name = all_names.pop()
        
        for mv in movers:
            self.LOG.info("Pre-trained model '{}' will be available in this training".format(mv.show()))
        
        train: Training = super().new(
            name=name,
            proj=self.proj,
            bvers=None if bv is None else bv.to_embedded(),
            notebook=assert_extension(notebook, Extension.IPYNB),
            details=join_dicts(details or {}, dict(params=params or {}), allow_overwrite=False),
            _duplicate_filter=dict(name=name, proj=self.proj)
        )
        
        TrainingExp(
            train=train,
            tag=tag,
            datasets=datasets,
            movers=movers,
            resource_profile=kwargs.pop('resource_profile', None),
            log=self.LOG
        ).launch(**kwargs)
        
        self.reset_logger()
        return train.reload()


class TrainingExp(ShortExpedition):
    
    section = DockerConst.Section.TRAIN
    
    def __init__(self, train: Training, tag=DockerConst.LATEST, **kwargs):
        
        self.train = train
        super().__init__(
            proj=train.proj,
            tag=tag,
            docs=[train],
            **kwargs
        )
    
    def close(self, completed: bool = False):
        
        try:
            super().close(completed)
            
            if self.captain.interrupted or not completed:
                self.LOG.warn('Failing training due to an interruption')
                self.train.reload()
                self.train.task.state = Task.State.FAILED
                self.train.save()
        
        except Exception:
            self.LOG.error("Failed to close training '{}'".format(self.make_alias()))
    
    def make_alias(self):
        
        return '{}-{}'.format(self.proj.name, self.train.name)
    
    def make_cmd(self):
        
        return [
            OnBoard.ENTRYPOINT,
            '--notebook-path',
            self.train.notebook,
            '--params',
            json.dumps(self.train.details['params'])
        ] + (['--debug'] if self.LOG.debug_mode else [])
