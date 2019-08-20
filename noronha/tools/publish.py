# -*- coding: utf-8 -*-

from noronha.api.movers import ModelVersionAPI
from noronha.db.proj import Project
from noronha.db.ds import Dataset
from noronha.db.train import Training
from noronha.common.constants import OnBoard


class Publisher(object):
    
    def __init__(self):
        
        self.mv_api = ModelVersionAPI()
        self.mv_api.proj = Project().load()
        self.ds = Dataset().load(ignore=True)
        self.train = Training().load(ignore=True)
    
    def __call__(self, src_path: str = None, name: str = None, details: dict = None):
        
        return self.mv_api.new(
            name=name or self.train.name,
            model=self.mv_api.proj.model.name,
            ds=self.ds.name,
            train=self.train.name,
            path=src_path or OnBoard.SHARED_MODEL_DIR,
            details=details or {},
            _replace=True
        )
