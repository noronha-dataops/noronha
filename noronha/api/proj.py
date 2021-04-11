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

import os
from typing import Type

from noronha.api.main import NoronhaAPI
from noronha.bay.anchor import LocalRepository, GitRepository, DockerRepository
from noronha.bay.shipyard import ImageSpec, RepoHandler, get_builder_class
from noronha.common.annotations import projected, validate
from noronha.common.constants import DockerConst
from noronha.common.errors import NhaAPIError
from noronha.common.logging import LOG
from noronha.db.proj import Project
from noronha.db.bvers import BuildVersion
from noronha.db.model import Model


class ProjectAPI(NoronhaAPI):
    
    doc = Project
    valid = NoronhaAPI.valid
    
    @projected
    def info(self):
        
        return self.proj.pretty()
    
    @projected
    def rm(self):
        
        return super().rm(target=self.proj)
    
    @validate(name=valid.dns_safe)
    def new(self, repo=None, models: list = None, home_dir: str = None, **kwargs):
        
        if models:
            finder = Model().find_one
            models = [finder(name=model_name) for model_name in models]
        else:
            models = []
            LOG.warn(
                "No models specified for the new project. "
                "When publishing a model version this project must specify its model name."
            )
        
        if home_dir is None:
            LOG.warn("No home directory was specified for the new project.")
            if self._decide("Would you like to use the current working directory?", default=False):
                home_dir = os.getcwd()
                LOG.info("Using as home directory: {}".format(home_dir))
        
        return super().new(
            home_dir=None if home_dir is None else LocalRepository(home_dir).address,
            models=models,
            **kwargs
        )
    
    @projected
    def update(self, models: list = None, **kwargs):
        
        if models:
            kwargs['models'] = [
                Model.find_one(name=model_name)
                for model_name in models
            ]
        
        if 'home_dir' in kwargs:
            kwargs['home_dir'] = LocalRepository(kwargs['home_dir']).address
        
        return super().update(
            filter_kwargs=dict(name=self.proj.name),
            update_kwargs=kwargs
        )
    
    @projected
    def build(self, tag=DockerConst.LATEST, from_here=False, from_home=False, from_git=False, pre_built=False,
              nocache: bool = False):
        
        flags = [from_here, from_home, from_git, pre_built]
        pairs = zip([None, LocalRepository, GitRepository, DockerRepository], flags)
        chosen = list(filter(lambda pair: pair[1], pairs))
        
        if True in flags:
            assert len(chosen) == 1, NhaAPIError("Got ambiguous 'build from' flags")
            repo_cls = chosen[0][0]
        else:
            repo_cls = None
        
        if repo_cls is None:
            repo = LocalRepository('.')
        else:
            repo = repo_cls.from_project(self.proj)
        
        bvers = BuildVersion(
            tag=tag,
            proj=self.proj.name,
            built_from=repo.builds_from
        )
        
        builder_cls: Type[RepoHandler] = get_builder_class(source_repo=repo)
        builder = builder_cls(repo=repo, img_spec=ImageSpec.from_bvers(bvers))
        
        bvers.docker_id = builder.build(nocache=nocache)
        bvers.git_version = repo.git_version
        bvers.save(built_now=True)
        return bvers
