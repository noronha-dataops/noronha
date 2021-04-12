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

import json

from noronha.api.main import NoronhaAPI
from noronha.bay.expedition import LongExpedition
from noronha.common.annotations import validate, projected
from noronha.common.constants import DockerConst, Extension, OnBoard, OnlineConst, EnvVar
from noronha.common.parser import assert_extension, join_dicts
from noronha.db.bvers import BuildVersion
from noronha.db.depl import Deployment
from noronha.db.movers import ModelVersion


class DeploymentAPI(NoronhaAPI):
    
    doc = Deployment
    valid = NoronhaAPI.valid
    
    def set_logger(self, name):
        
        super().set_logger(
            name='-'.join([
                DockerConst.Section.DEPL,
                self.proj.name,
                name
            ])
        )
    
    @projected
    def info(self, name):
        
        return self.doc.find_one(
            name=name,
            proj=self.proj.name
        ).save().reload().pretty()  # save operation triggers cleaning of failed tasks
    
    @projected
    def rm(self, name):
        
        depl = self.doc.find_one(name=name, proj=self.proj.name)
        DeploymentExp(depl).revert()
        depl.delete()
        return super().rm(target=depl)
    
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
    def new(self, name: str = None, tag=DockerConst.LATEST, notebook: str = 'predict', details: dict = None,
            params: dict = None, movers: list = None, port: int = None, _replace: bool = None, **kwargs):
        
        self.set_logger(name)
        bv = BuildVersion.find_one_or_none(tag=tag, proj=self.proj)
        
        depl = super().new(
            name=name,
            proj=self.proj,
            movers=[ModelVersion.find_by_pk(mv).to_embedded() for mv in movers or []],
            bvers=None if bv is None else bv.to_embedded(),
            notebook=assert_extension(notebook, Extension.IPYNB),
            details=join_dicts(details or {}, dict(params=params or {}), allow_overwrite=False),
            replicas=kwargs.get('tasks'),
            host_port=port,
            _duplicate_filter=dict(name=name, proj=self.proj)
        )
        
        # TODO: check consistensy of project, docker tag and git version between depl.bvers and movers.bvers
        exp = DeploymentExp(
            depl,
            port,
            tag,
            resource_profile=kwargs.pop('resource_profile', None),
            log=self.LOG
        )
        exp.launch(**kwargs)

        if port is None:
            node_port = exp.captain.get_node_port(exp.make_name())
            depl.reload()
            depl.update(host_port=node_port)

        self.reset_logger()
        return depl


class DeploymentExp(LongExpedition):
    
    section = DockerConst.Section.DEPL
    
    def __init__(self, depl: Deployment, port: int = None, tag=DockerConst.LATEST, **kwargs):
        
        self.depl = depl
        self.port = port
        super().__init__(
            proj=depl.proj,
            tag=tag,
            movers=self.depl.movers,
            docs=[depl],
            **kwargs
        )
    
    @property
    def additional_launch_kwargs(self):
        
        return dict(
            allow_probe=not self.mock
        )
    
    def make_env_vars(self):
        
        return join_dicts(super().make_env_vars(), {
            EnvVar.OPEN_SEA: 'Yes'
        })
    
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
        ] + (['--debug'] if self.LOG.debug_mode else [])
