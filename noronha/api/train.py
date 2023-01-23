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
import traceback

from noronha.api.main import NoronhaAPI
from noronha.bay.compass import DeploymentCompass
from noronha.bay.expedition import ShortExpedition
from noronha.common.annotations import validate, projected, retry_when_none
from noronha.common.constants import DockerConst, Extension, OnBoard, Task
from noronha.common.errors import DBError
from noronha.common.parser import assert_extension, join_dicts
from noronha.db.bvers import BuildVersion
from noronha.db.depl import Deployment
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
            target_deploy: str = None, **kwargs):
        
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

        exp = TrainingExp(
            train=train,
            tag=tag,
            datasets=datasets,
            movers=movers,
            resource_profile=kwargs.pop('resource_profile', None),
            log=self.LOG
        )
        
        kwargs['is_job'] = True
        exp.launch(**kwargs)
        train.reload()

        if target_deploy is not None and train.task.state == Task.State.FINISHED:
            self._update_deploy(target_deploy, train)

        self.reset_logger()
        return train.reload()

    def _update_deploy(self, target_deploy: str, train: Training):

        self.LOG.info("Deploy '{}' was provided, attempting to update recently trained model".format(target_deploy))
        updated = False

        try:
            depl = Deployment.find_one(name=target_deploy, proj=self.proj.name)  # may throw DBError.NotFound
            depl_compass = DeploymentCompass(depl)
            endpoints = depl_compass.get_endpoints()

            if len(endpoints) == 0:
                self.LOG.warn("Could not determine service port, skipping model update")

            status = "failed"
            for url in endpoints:
                url += '/update'
                response = self._update_mover(url, train.mover.name)

                if response:
                    updated = True
                    status = "succeeded"
                else:
                    updated = False
                    status = "failed"
                    break

            self.LOG.info("Update model version {}:{} {}".format(train.mover.model.name, train.mover.name, status))

        except DBError.NotFound:
            self.LOG.error("Could not find deploy named: {} in project: {}. Skipping model update"
                           .format(target_deploy, self.proj.name))

        train.update(deploy_update=updated)

    @retry_when_none(10)
    def _update_mover(self, url: str, mover: str):

        import requests

        r = requests.post(url, params={'model_version': mover})

        if r.status_code != 200:
            self.LOG.debug("Model version '{}' update failed, retrying...".format(mover))
            return False
        else:
            return True


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
                traceback.print_exc()
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
