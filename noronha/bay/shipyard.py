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

"""Module for handling Docker images"""

import json
from abc import ABC, abstractmethod

from noronha.bay.anchor import Repository, DockerRepository, LocalRepository, GitRepository
from noronha.bay.compass import DockerCompass
from noronha.bay.utils import Workpath
from noronha.common.constants import DockerConst, FrameworkConst, Regex
from noronha.common.errors import NhaDockerError, ResolutionError
from noronha.common.logging import LOG
from noronha.common.parser import assert_dict
from noronha.db.bvers import BuildVersion
from noronha.db.proj import Project


class ImageSpec(object):
    
    def __init__(self, registry: str = None, section: str = None, image: str = None, tag: str = None,
                 pushable: bool = False):
        
        assert image is not None
        self.registry = registry or ''
        self.section = section or ''
        self.image = image
        self.tag = tag or DockerConst.LATEST
        self.pushable = pushable
    
    @classmethod
    def from_proj(cls, proj: Project, tag: str = DockerConst.LATEST):
        
        repo = DockerRepository(proj.docker_repo)
        
        return cls(
            registry=repo.registry,
            image=repo.image,
            tag=tag,
            pushable=False
        )
    
    @classmethod
    def from_bvers(cls, bvers: BuildVersion):
        
        configured_registry = DockerCompass().registry
        
        return cls(
            registry=configured_registry or DockerConst.LOCAL_REGISTRY,
            section=DockerConst.Section.PROJ,
            image=bvers.proj.name,
            tag=bvers.tag,
            pushable=True if configured_registry else False
        )
    
    @classmethod
    def for_island(cls, alias: str):
        
        configured_registry = DockerCompass().registry
        
        return cls(
            registry=configured_registry,
            section=DockerConst.Section.ISLE,
            image=alias,
            tag=FrameworkConst.FW_TAG,
            pushable=True if configured_registry else False
        )
    
    @property
    def name_with_prefix(self):
        
        return '{}-{}'.format(self.section, self.image).lstrip('-')
    
    @property
    def repo(self):
        
        return '{}/{}'.format(self.registry, self.name_with_prefix).lstrip('/')
    
    @property
    def target(self):
        
        return '{}:{}'.format(self.repo, self.tag)
    
    def untag(self):
        
        try:
            DockerCompass().get_api().remove_image(self.target)
        except Exception as e:
            LOG.error(e)
            return False
        else:
            return True


class RepoHandler(ABC):
    
    def __init__(self, repo: Repository, img_spec: ImageSpec):
        
        self.repo = repo
        self.img_spec = img_spec
    
    @abstractmethod
    def build(self, nocache: bool = False):
        
        raise NotImplementedError()


class DockerTagger(RepoHandler):
    
    def __init__(self, repo: Repository, img_spec: ImageSpec):
        
        super().__init__(repo=repo, img_spec=img_spec)
        self.repo: DockerRepository = self.repo  # enforcing repository subtype
        self.docker = DockerCompass().get_api()
        self.image: dict = None
    
    def build(self, nocache: bool = False):
        
        source = '{}:{}'.format(self.repo.address, self.img_spec.tag)
        LOG.info("Moving pre-built image from {} to {}".format(source, self.img_spec.target))
        self.docker.pull(self.repo.address, tag=self.img_spec.tag)
        self.image = self.docker.images(source)[0]
        self.tag_image()
        self.push_image()
        return self.image_id
    
    @property
    def image_id(self):
        
        return self.image['Id']
    
    def tag_image(self):
        
        self.docker.tag(
            image=self.image_id,
            repository=self.img_spec.repo,
            tag=self.img_spec.tag
        )
    
    def push_image(self):
        
        if self.img_spec.pushable:
            LOG.info("Pushing {}".format(self.img_spec.target))
            log = self.docker.push(self.img_spec.repo, tag=self.img_spec.tag)
            outcome = json.loads(Regex.LINE_BREAK.split(log.strip())[-1])
            
            if 'error' in outcome:
                raise NhaDockerError(
                    "Failed to push image '{}'. Error: {}"
                    .format(self.img_spec.target, outcome.get('errorDetail'))
                )
        else:
            LOG.warn("Docker registry is not configured. Skipping image push.")


class LocalBuilder(DockerTagger):
    
    def build(self, nocache: bool = False):
        
        work_path = None
        
        try:
            LOG.info("Building {} from {}".format(self.img_spec.target, self.repo.address))
            work_path = self.make_work_path()
            build_path = self.deploy_source(work_path)
            
            logs = self.docker.build(
                path=build_path,
                tag=self.img_spec.target,
                nocache=nocache,
                rm=True
            )
            
            self.print_logs(logs)
            self.image = self.docker.images(self.img_spec.target)[0]
        except Exception as e:
            raise NhaDockerError("Failed to build from {}".format(self.repo)) from e
        else:
            self.tag_image()
            self.push_image()
            return self.image_id
        finally:
            if work_path is not None:
                work_path.dispose()
    
    def deploy_source(self, work_path: Workpath) -> str:
        
        return work_path
    
    def make_work_path(self) -> Workpath:
        
        return Workpath.get_fixed(path=self.repo.address)
    
    def print_logs(self, logs):
        
        for line in logs:
            dyct = assert_dict(line)
            
            if 'stream' in dyct:
                message = dyct['stream'].strip()
                
                if message:
                    LOG.debug(message)
            
            if 'error' in dyct:
                raise NhaDockerError(dyct['error'].strip())


class GitBuilder(LocalBuilder):
    
    def __init__(self, repo: Repository, img_spec: ImageSpec):
        
        super().__init__(repo=repo, img_spec=img_spec)
        self.repo: GitRepository = self.repo  # enforcing repository subtype
    
    def deploy_source(self, work_path: Workpath) -> str:
        
        self.repo.clone(work_path)
        return work_path.join(self.repo.name)
    
    def make_work_path(self) -> Workpath:
        
        return Workpath.get_tmp()


def get_builder_class(source_repo: Repository):
    
    try:
        return {
            DockerRepository.__name__: DockerTagger,
            LocalRepository.__name__: LocalBuilder,
            GitRepository.__name__: GitBuilder
        }.get(source_repo.__class__.__name__)
    except KeyError:
        raise ResolutionError("No builder class found for '{}'".format(source_repo))
