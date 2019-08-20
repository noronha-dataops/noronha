# -*- coding: utf-8 -*-

import json

from noronha.api.main import NoronhaAPI
from noronha.bay.cargo import MetaCargo, LogsCargo, ConfCargo, MoversCargo, SharedCargo
from noronha.bay.expedition import LongExpedition
from noronha.common.annotations import validate, projected
from noronha.common.constants import DockerConst, Extension, OnBoard, OnlineConst
from noronha.common.errors import NhaAPIError
from noronha.common.logging import LOG
from noronha.common.utils import assert_extension, join_dicts
from noronha.db.bvers import BuildVersion
from noronha.db.depl import Deployment
from noronha.db.movers import ModelVersion


class DeploymentAPI(NoronhaAPI):
    
    doc = Deployment
    valid = NoronhaAPI.valid
    
    @projected
    def info(self, name):
        
        return super().info(name=name, proj=self.proj.name)
    
    @projected
    def rm(self, name):
        
        depl = self.doc().find_one(name=name, proj=self.proj.name)
        DeploymentExp(depl).revert()
        depl.delete()
    
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
        port=(int, None),
        params=(dict, None)
    )
    def new(self, name: str = None, tag=DockerConst.LATEST, notebook: str = None, details: dict = None,
            params: dict = None, movers: str = None, model: str = None, port: int = None, _replace: bool = None,
            **kwargs):
        
        if model is None:
            raise NhaAPIError("Cannot determine model version if parent model is not specified")
        
        bv = BuildVersion().find_one_or_none(tag=tag, proj=self.proj)
        
        depl = super().new(
            name=name,
            proj=self.proj,
            movers=ModelVersion().find_one(name=movers, model=model).to_embedded(),
            bvers=None if bv is None else bv.to_embedded(),
            notebook=assert_extension(notebook, Extension.IPYNB),
            details=join_dicts(details or {}, dict(params=params or {}), allow_overwrite=False),
            _duplicate_filter=dict(name=name, proj=self.proj)
        )
        
        # TODO: check consistensy of project, docker tag and git version between depl.bvers and movers.bvers
        DeploymentExp(depl, port, tag).launch(**kwargs)
        return depl


class DeploymentExp(LongExpedition):
    
    section = DockerConst.Section.DEPL
    
    def __init__(self, depl: Deployment, port: int = None, tag=DockerConst.LATEST):
        
        self.depl = depl
        self.port = port
        super().__init__(proj=depl.proj, tag=tag)
    
    def make_ports(self):
        
        if self.port is None:
            return [
                '{}'.format(OnlineConst.PORT)  # containerPort reference without a nodePort mapping
            ]
        else:
            return [
                '{}:{}'.format(self.port, OnlineConst.PORT)
            ]
    
    def make_alias(self):
        
        return '{}-{}'.format(self.proj.name, self.depl.name)
    
    def make_cmd(self):
        
        return [
            OnBoard.ENTRYPOINT,
            '--notebook-path',
            self.depl.notebook,
            '--params',
            json.dumps(self.depl.details['params']),
        ] + (['--debug'] if LOG.debug_mode else [])
    
    def make_vols(self):
        
        suffix = '{}-{}'.format(self.proj.name, self.depl.name)
        docs = [self.proj, self.bvers, self.depl]
        
        cargos = [
            MetaCargo(suffix=suffix, docs=docs),
            ConfCargo(suffix=suffix),
            MoversCargo(self.depl.movers)
        ]
        
        return [
            LogsCargo(suffix=suffix),
            SharedCargo(suffix, cargos)
        ]
