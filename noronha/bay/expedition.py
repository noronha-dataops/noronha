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

"""TODO: {{module description}}
"""

from abc import ABC, abstractmethod
from typing import List

from noronha.bay.captain import get_captain, Captain
from noronha.bay.cargo import Cargo, DatasetCargo, MetaCargo, ConfCargo, LogsCargo, SharedCargo, MoversCargo,\
    TimezoneCargo
from noronha.bay.compass import DockerCompass
from noronha.bay.shipyard import ImageSpec
from noronha.common.constants import DockerConst, EnvVar
from noronha.common.logging import Logged
from noronha.common.parser import join_dicts
from noronha.db.proj import Project
from noronha.db.bvers import BuildVersion
from noronha.db.ds import Dataset
from noronha.db.main import SmartBaseDoc
from noronha.db.movers import ModelVersion


class Expedition(Logged, ABC):
    
    section = None
    is_fleet = False
    
    def __init__(self, img_spec: ImageSpec = None, proj: Project = None, tag: str = DockerConst.LATEST,
                 movers: List[ModelVersion] = None, datasets: List[Dataset] = None, docs: List[SmartBaseDoc] = None,
                 **kwargs):
        
        Logged.__init__(self, log=kwargs.get('log'))
        self.docker_compass = DockerCompass()
        self.mock = self.docker_compass.mock
        self.captain: Captain = get_captain(section=self.section, **kwargs)
        self.launcher = self.captain.deploy if self.is_fleet else self.captain.run
        self.proj, self.bvers, self.img_spec = self._infer_img_spec(img_spec, proj, tag)
        self.docs = docs or []
        self.movers = movers or []
        self.datasets = datasets or []
        self.docs += self.movers
        self.docs += self.datasets
        
        if self.proj is not None:
            self.docs.append(self.proj)
        
        if self.bvers is not None:
            self.docs.append(self.bvers)
        
        self.cargos = self.make_vols()
    
    @property
    def additional_launch_kwargs(self):
        
        return {}
    
    def _infer_img_spec(self, img_spec: ImageSpec = None, proj: Project = None, tag: str = DockerConst.LATEST):
        
        if img_spec is None:
            bvers = BuildVersion.find_one_or_none(tag=tag, proj=proj)
            
            if bvers is None:
                self.LOG.info(
                    "Build version {}:{} not found. Using project's Docker repository directly: {}:{}"
                    .format(proj.name, tag, proj.docker_repo, tag)
                )
                img_spec = ImageSpec.from_proj(proj, tag)
            else:
                img_spec = ImageSpec.from_bvers(bvers)
        else:
            bvers = None
        
        return proj, bvers, img_spec
    
    def launch(self, env_vars: dict = None, mounts: list = None, ports: list = None, **kwargs):
        
        self.launcher(
            name=self.make_name(),
            img=self.img_spec,
            env_vars=join_dicts(env_vars or {}, self.make_env_vars(), allow_overwrite=False),
            mounts=(mounts or []),
            cargos=self.cargos,
            ports=(ports or []) + self.make_ports(),
            cmd=DockerConst.HANG_CMD if self.mock else self.make_cmd(),
            **self.additional_launch_kwargs,
            **kwargs
        )
        
        return True
    
    def make_vols(self):
        
        kwargs = dict(section=self.section, alias=self.make_alias())
        conf_cargo = ConfCargo(**kwargs)
        meta_cargo = MetaCargo(**kwargs, docs=self.docs)
        
        ds_cargos = [
            DatasetCargo(ds, section=self.section, log=self.LOG)
            for ds in self.datasets
        ]
        
        mv_cargos = [
            MoversCargo(mv, section=self.section, log=self.LOG)
            for mv in self.movers
        ]
        
        return [
            LogsCargo(**kwargs),
            TimezoneCargo(**kwargs),
            SharedCargo(
                **kwargs,
                cargos=[conf_cargo, meta_cargo] + ds_cargos + mv_cargos
            )
        ]
    
    @abstractmethod
    def make_alias(self):
        
        pass
    
    def make_name(self):
        
        return '{}-{}'.format(self.section, self.make_alias())
    
    def make_env_vars(self):
        
        return {
            EnvVar.CONTAINER_PURPOSE: self.section
        }
    
    def make_cmd(self):
        
        return [
            # arguments for the container's entrypoint
        ]
    
    def make_ports(self):
        
        return [
            # port mappings
        ]


class ShortExpedition(Expedition, ABC):
    
    def launch(self, foreground: bool = True, **kwargs):
        
        completed = False
        
        try:
            completed = super().launch(foreground=foreground, **kwargs)
        finally:
            self.close(completed)
    
    def close(self, completed: bool = False):
        
        try:
            self.captain.dispose_run(self.make_name())
            
            for cargo in self.cargos:
                if isinstance(cargo, LogsCargo) and (self.LOG.debug_mode or not completed):
                    self.LOG.debug("Keeping logs from volume '{}'".format(cargo.name))
                else:
                    self.captain.rm_vol(cargo, ignore=True)
            
            self.captain.close()
        except Exception:
            self.LOG.warn("Failed to close resource '{}'".format(self.captain.__class__.__name__))


class LongExpedition(Expedition, ABC):
    
    is_fleet = True
    
    def launch(self, **kwargs):
        
        try:
            super().launch(**kwargs)
        except Exception as e:
            self.revert(ignore_vols=True)
            raise e
        finally:
            self.close()
    
    def revert(self, ignore_vols=False):
        
        try:
            self.captain.dispose_deploy(self.make_name())
            
            for cargo in self.cargos:
                if isinstance(cargo, LogsCargo) and self.LOG.debug_mode:
                    self.LOG.debug("Keeping logs from volume '{}'".format(cargo.name))
                else:
                    self.captain.rm_vol(cargo, ignore=ignore_vols)
            
            self.close()
        except Exception as e:
            self.LOG.error("Failed to revert deployment of '{}'".format(self.make_alias()))
            self.LOG.error(e)
    
    def close(self):
        
        try:
            self.captain.close()
        except Exception:
            self.LOG.error("Failed to close resource '{}'".format(self.captain.__class__.__name__))
