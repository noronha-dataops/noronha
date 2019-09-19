# -*- coding: utf-8 -*-

import os
from datetime import datetime

from noronha.api.main import NoronhaAPI
from noronha.bay.anchor import resolve_repo, DockerRepository
from noronha.bay.shipyard import get_builder_class
from noronha.common.annotations import projected, validate
from noronha.common.constants import DockerConst
from noronha.common.errors import NhaAPIError, MisusageError
from noronha.common.logging import LOG
from noronha.db.proj import Project
from noronha.db.bvers import BuildVersion
from noronha.db.model import Model


class ProjectAPI(NoronhaAPI):
    
    doc = Project
    valid = NoronhaAPI.valid
    
    @projected
    def info(self):
        
        return self.proj.expanded()
    
    @projected
    def rm(self):
        
        return self.proj.delete()
    
    @validate(name=valid.dns_safe)
    def new(self, repo=None, models: list = None, **kwargs):
        
        if repo is None:
            if self.scope == self.Scope.CLI:
                repo = os.getcwd()
                LOG.warn("No repository was specified for the new project. Using current directory: {}".format(repo))
            else:
                raise NhaAPIError("Project's repository cannot be None")
        
        if not models:
            models = []
            LOG.warn(
                "No models specified for the new project. "
                "When publishing a model version this project must specify its model name."
            )
        else:
            finder = Model().find_one
            models = [finder(name=model_name) for model_name in models]
        
        return super().new(
            repo=resolve_repo(repo, implicit_local=True).address,
            models=models,
            **kwargs
        )
    
    @projected
    def update(self, models: list = None, **kwargs):
        
        if models:
            finder = Model().find_one
            kwargs['models'] = [finder(name=model_name) for model_name in models]
        
        return super().update(
            filter_kwargs=dict(name=self.proj.name),
            update_kwargs=kwargs
        )
    
    @projected
    def build(self, tag=DockerConst.LATEST, **kwargs):
        
        repo_obj = resolve_repo(self.proj.repo)
        
        assert not isinstance(repo_obj, DockerRepository), MisusageError(
            "This project's repository is already a Docker repository, so its builds are managed by the maintainer")
        
        builder_cls = get_builder_class(source_repo=repo_obj)
        builder_obj = builder_cls(target_name=self.proj.name, target_tag=tag, section=DockerConst.Section.PROJ)
        return BuildVersion(
            tag=tag,
            proj=self.proj,
            git_version=repo_obj.git_hash,
            docker_id=builder_obj(source_repo=repo_obj, **kwargs),
            built_at=datetime.now()
        ).save()
