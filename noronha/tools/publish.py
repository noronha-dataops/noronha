# -*- coding: utf-8 -*-

from noronha.api.movers import ModelVersionAPI
from noronha.bay.cargo import MoversCargo, MetaCargo
from noronha.common.constants import Paths, DockerConst
from noronha.common.errors import ResolutionError
from noronha.common.logging import LOG
from noronha.db.proj import Project
from noronha.db.train import Training
from noronha.tools.shortcuts import dataset_meta, movers_meta, get_purpose


class Publisher(object):
    
    def __init__(self):
        
        self.proj = Project.load()
        self.train = Training.load(ignore=True)
        self.mv_api = ModelVersionAPI(self.proj)
    
    def _infer_parent_model(self, model_name: str = None):
        
        if model_name is None:
            n_models = len(self.proj.models)
            
            if n_models == 1:
                model_name = self.proj.models[0].name
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
        
        assert isinstance(model_name, str) and len(model_name) > 0
        return model_name
    
    def _infer_dataset(self, model_name: str, uses_dataset: bool = True, dataset_name: str = None):
        
        if uses_dataset:
            return dataset_meta(model=model_name, dataset=dataset_name).name
        else:
            return None
    
    def _infer_pretrained(self, uses_pretrained: bool = False, pretrained_with: str = None):
        
        if uses_pretrained:
            model_name, version_name = (pretrained_with or ':').split(':')
            mv = movers_meta(model=model_name or None, version=version_name or None)
            return mv.show()
        else:
            return None
    
    def __call__(self, src_path: str = Paths.TMP, details: dict = None,
                 version_name: str = None, model_name: str = None,
                 uses_dataset: bool = True, dataset_name: str = None,
                 uses_pretrained: bool = False, pretrained_with: str = None):
        
        model_name = self._infer_parent_model(model_name)
        
        mv = self.mv_api.new(
            name=version_name or self.train.name,
            model=model_name,
            ds=self._infer_dataset(model_name, uses_dataset, dataset_name),
            train=self.train.name,
            path=src_path,
            details=details or {},
            pretrained=self._infer_pretrained(uses_pretrained, pretrained_with),
            _replace=True
        )
        
        if get_purpose() == DockerConst.Section.IDE:
            LOG.info("For testing purposes, model files will be moved to the deployed model path")
            MoversCargo(mv, local=True).move(src_path)
            MetaCargo(docs=[mv]).deploy()
        
        return mv
