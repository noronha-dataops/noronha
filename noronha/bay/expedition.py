# -*- coding: utf-8 -*-

from abc import ABC
import random_name

from noronha.bay.captain import get_captain, Captain
from noronha.bay.cargo import LogsCargo
from noronha.bay.compass import DockerCompass
from noronha.bay.shipyard import ImageSpec
from noronha.common.constants import DockerConst
from noronha.common.logging import LOG
from noronha.common.utils import join_dicts
from noronha.db.proj import Project
from noronha.db.bvers import BuildVersion


class Expedition(ABC):
    
    section = None
    is_fleet = False
    
    def __init__(self, img_spec: ImageSpec = None, proj: Project = None, tag: str = DockerConst.LATEST):
        
        self.docker_compass = DockerCompass()
        self.captain: Captain = get_captain(section=self.section)
        self.cargos = []
        self.targets = None
        self.mock = False
        
        if self.is_fleet:
            self.launcher = self.captain.deploy
        else:
            self.launcher = self.captain.run
        
        if img_spec is None:
            self.proj = proj
            self.bvers = BuildVersion().find_one_or_none(tag=tag, proj=proj)
            self.img_spec = ImageSpec.from_repo_or_bvers(proj, tag, self.bvers)
        else:
            self.img_spec = img_spec
    
    def launch(self, env_vars: dict = None, mounts: list = None, ports: list = None, **kwargs):
        
        self.cargos = self.make_vols()
        
        self.launcher(
            alias=self.make_alias(),
            img=self.img_spec,
            env_vars=join_dicts(env_vars or {}, self.make_env_vars(), allow_overwrite=False),
            mounts=(mounts or []),
            cargos=self.cargos,
            ports=(ports or []) + self.make_ports(),
            cmd=DockerConst.HANG_CMD if self.mock else self.make_cmd(),
            **kwargs
        )
    
    def make_alias(self):
        
        return random_name.generate_name(separator='-')  # will be used as suffix for the container name
    
    def make_env_vars(self):
        
        return {
            # env vars to set inside the container
        }
    
    def make_vols(self):
        
        return [
            # volumes (cargos) to be mounted in the container
        ]
    
    def make_cmd(self):
        
        return [
            # arguments for the container's entrypoint
        ]
    
    def make_ports(self):
        
        return [
            # port mappings
        ]


class ShortExpedition(Expedition):
    
    def launch(self, foreground: bool = True, **kwargs):
        
        try:
            super().launch(foreground=foreground, **kwargs)
        finally:
            self.close()
    
    def close(self):
        
        self.captain.dispose_run(self.make_alias(), force=True)
        
        for cargo in self.cargos:
            if isinstance(cargo, LogsCargo) and LOG.debug_mode:
                LOG.debug("Keeping logs from volume '{}'".format(cargo.full_name))
            else:
                self.captain.rm_vol(cargo, force=True)
        
        self.captain.close()


class LongExpedition(Expedition):
    
    is_fleet = True
    
    def launch(self, **kwargs):
        
        try:
            super().launch(**kwargs)
        except Exception as e:
            LOG.error(e)
            self.revert()
        finally:
            self.close()
    
    def revert(self):
        
        self.captain.dispose_deploy(self.make_alias(), force=True)
        
        for cargo in self.cargos:
            if isinstance(cargo, LogsCargo) and LOG.debug_mode:
                LOG.debug("Keeping logs from volume '{}'".format(cargo.full_name))
            else:
                self.captain.rm_vol(cargo, force=True)
    
    def close(self):
        
        self.captain.close()
