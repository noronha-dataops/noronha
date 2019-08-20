# -*- coding: utf-8 -*-

from noronha.api.main import NoronhaAPI
from noronha.bay.cargo import MetaCargo, ConfCargo, SharedCargo
from noronha.bay.expedition import ShortExpedition
from noronha.common import NoteConst
from noronha.common.annotations import projected, validate
from noronha.common.constants import DockerConst, OnBoard
from noronha.common.logging import LOG


class NotebookAPI(NoronhaAPI):
    
    valid = NoronhaAPI.valid
    
    @projected
    @validate(env_vars=dict, mounts=list, port=(int, None), tag=(str, None))
    def __call__(self, tag: str = DockerConst.LATEST, port: int = NoteConst.HOST_PORT, **kwargs):
        
        return NotebookExp(port=port, proj=self.proj, tag=tag).launch(**kwargs)


class NotebookExp(ShortExpedition):
    
    section = DockerConst.Section.IDE
    
    def __init__(self, port: int = NoteConst.HOST_PORT, **kwargs):
        
        self.port = port
        super().__init__(**kwargs)
    
    def make_cmd(self):
        
        return [
            OnBoard.ENTRYPOINT
        ] + (['--debug'] if LOG.debug_mode else [])
    
    def make_alias(self):
        
        return self.proj.name
    
    def make_ports(self):
        
        return [
            '{}:{}'.format(self.port, NoteConst.ORIGINAL_PORT)
        ]
    
    def make_vols(self):
        
        suffix = self.proj.name
        docs = [self.proj]
        
        if self.bvers is not None:
            docs.append(self.bvers)
        
        cargos = [
            MetaCargo(suffix=suffix, docs=docs),
            ConfCargo(suffix=suffix)
        ]
        
        return [
            SharedCargo(suffix, cargos)
        ]
