# -*- coding: utf-8 -*-

import os

from noronha.api.movers import ModelVersionAPI
from noronha.common.constants import OnBoard, Paths
from noronha.common.errors import NhaConsistencyError, ResolutionError
from noronha.db.ds import Dataset
from noronha.db.movers import ModelVersion
from noronha.db.proj import Project
from noronha.db.train import Training


class Publisher(object):
    
    def __init__(self):
        
        self.proj = Project().load()
        self.mv_api = ModelVersionAPI().set_proj(self.proj)
        self.ds = Dataset().load(ignore=True)
        self.train = Training().load(ignore=True)
        self.pretrained: ModelVersion = ModelVersion().load(ignore=True)
    
    def __call__(self, src_path: str = Paths.TMP, name: str = None, details: dict = None, model: str = None,
                 uses_pretrained=False):
        
        return self.mv_api.new(
            name=name or self.train.name,
            model=self.validate_parent_model(model),
            ds=self.ds.name,
            train=self.train.name,
            path=src_path,
            details=details or {},
            pretrained=self.validate_pretrained(uses_pretrained),
            _replace=True
        )
    
    def validate_parent_model(self, model: str = None):
        
        if model is None:
            n_models = len(self.proj.models)
            
            if n_models == 1:
                model = self.proj.models[0].name
                err = None
            elif n_models == 0:
                err = "Project '{proj}' does not include any models."
            else:
                err = "Project '{proj}' includes {n_models} models."
            
            if err is not None:
                raise ResolutionError(
                    err.format(proj=self.proj.name, n_models=n_models)
                    + " Please specify which model you are publishing"
                )
        
        assert isinstance(model, str) and len(model) > 0
        return model
    
    def validate_pretrained(self, uses_pretrained: bool):
        
        if not uses_pretrained:
            return None
        elif not os.path.isdir(OnBoard.LOCAL_PRET_MODEL_DIR) or not os.listdir(OnBoard.LOCAL_PRET_MODEL_DIR):
            raise NhaConsistencyError(
                "No files were found in pre-trained model directory. Are you sure your model uses a pre-trained?")
        elif self.pretrained is None:
            raise NhaConsistencyError(
                "No model version was found in metadata directory. Are you sure your model uses a pre-trained?")
        else:
            return self.pretrained.reference
