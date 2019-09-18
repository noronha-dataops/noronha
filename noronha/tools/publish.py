# -*- coding: utf-8 -*-

import os

from noronha.api.movers import ModelVersionAPI
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.proj import Project
from noronha.db.train import Training
from noronha.common.constants import OnBoard
from noronha.common.errors import NhaConsistencyError


class Publisher(object):
    
    def __init__(self):
        
        self.mv_api = ModelVersionAPI()
        self.mv_api.proj = Project().load()
        self.ds = Dataset().load(ignore=True)
        self.train = Training().load(ignore=True)
        self.pretrained: ModelVersion = ModelVersion().load(ignore=True)
    
    def __call__(self, src_path: str = None, name: str = None, details: dict = None, uses_pretrained=False):
        
        return self.mv_api.new(
            name=name or self.train.name,
            model=self.mv_api.proj.model.name,
            ds=self.ds.name,
            train=self.train.name,
            path=src_path or OnBoard.SHARED_MODEL_DIR,
            details=details or {},
            pretrained=self.validate_pretrained(uses_pretrained),
            _replace=True
        )
    
    def validate_pretrained(self, uses_pretrained: bool):
        
        if not uses_pretrained:
            return None
        elif not os.listdir(OnBoard.LOCAL_PRET_MODEL_DIR):
            raise NhaConsistencyError(
                "No files were found in pre-trained model directory. Are you sure your model uses a pre-trained?")
        elif self.pretrained is None:
            raise NhaConsistencyError(
                "No model version was found in metadata directory. Are you sure your model uses a pre-trained?")
        else:
            return self.pretrained.reference
