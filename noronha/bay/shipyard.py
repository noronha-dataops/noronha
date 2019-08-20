# -*- coding: utf-8 -*-

"""Module for handling Docker images"""

import git
from abc import ABC, abstractmethod

from noronha.bay.anchor import Repository, DockerRepository, LocalRepository, GitRepository, resolve_repo
from noronha.bay.compass import DockerCompass
from noronha.bay.utils import Workpath
from noronha.common.annotations import Configured
from noronha.common.conf import DockerConf
from noronha.common.constants import DockerConst
from noronha.common.errors import NhaDockerError, ResolutionError
from noronha.common.logging import LOG
from noronha.common.utils import assert_dict
from noronha.db.bvers import BuildVersion
from noronha.db.proj import Project


class ImageSpec(object):
    
    def __init__(self, section: str = DockerConst.Section.PROJ, name: str = None, tag: str = DockerConst.LATEST,
                 third_party=False):
        
        self.compass = DockerCompass()
        self.section = section
        self.name = name
        self.tag = tag
        
        if third_party:
            self.section = ''
            self.registry = ''
            self.pushable = False
        else:
            configured_registry = self.compass.registry
            
            if configured_registry is None:
                self.registry = DockerConst.LOCAL_REGISTRY
                self.pushable = False
            else:
                self.registry = configured_registry
                self.pushable = True
    
    @property
    def name_with_prefix(self):
        
        return '{}-{}'.format(self.section, self.name).lstrip('-')
    
    @property
    def repo(self):
        
        return '{}/{}'.format(self.registry, self.name_with_prefix).lstrip('/')
    
    @property
    def target(self):
        
        return '{}:{}'.format(self.repo, self.tag)
    
    @classmethod
    def from_bvers(cls, bvers: BuildVersion):
        
        return cls(section=DockerConst.Section.PROJ, name=bvers.proj.name, tag=bvers.tag)
    
    @classmethod
    def from_repo(cls, proj: Project, tag=DockerConst.LATEST):
        
        repo = resolve_repo(proj.repo)
        
        assert isinstance(repo, DockerRepository), ResolutionError(
            "Cannot find Docker image only by project and tag unless the project's repository is of type Docker")
        
        return cls(name=repo.path, tag=tag, third_party=True)
    
    @classmethod
    def from_repo_or_bvers(cls, proj: Project, tag=DockerConst.LATEST, bvers: BuildVersion = None):
        
        if bvers is not None:
            return cls.from_bvers(bvers)
        else:
            return cls.from_repo(proj, tag)


class RepoHandler(ABC):
    
    @abstractmethod
    def __call__(self, src_repo: Repository):
        
        raise NotImplementedError()


class DockerTagger(Configured, RepoHandler):
    
    conf = DockerConf
    
    def __init__(self, target_name: str, section: str = DockerConst.Section.PROJ,
                 target_tag: str = DockerConst.LATEST):
        
        self.compass = DockerCompass()
        self.img_spec = ImageSpec(section=section, name=target_name, tag=target_tag)
        self.docker = self.compass.get_api()
        self.image: dict = None
    
    def __call__(self, source_repo: DockerRepository):
        
        LOG.info("Pulling source repository {} and tagging/pushing to target {}"
                 .format(source_repo, self.img_spec.target))
        self.docker.pull(source_repo.full_repo_name, tag=source_repo.tag)
        self.image = self.docker.images('{}:{}'.format(source_repo.full_repo_name, source_repo.tag))[0]
        self.tag_image()
        self.push_image()
        return self.image_id
    
    @property
    def image_id(self):
        
        return self.image['Id']
    
    def tag_image(self):
        
        self.docker.tag(image=self.image_id, repository=self.img_spec.repo, tag=self.img_spec.tag)
    
    def push_image(self):
        
        if self.img_spec.pushable:
            LOG.info("Pushing {}".format(self.img_spec.target))
            self.docker.push(self.img_spec.repo, tag=self.img_spec.tag)
        else:
            LOG.warn("Remote Docker registry is not configured. Skipping image push")
    
    def untag(self):
        
        try:
            self.docker.remove_image(self.img_spec.target)
        except Exception as e:
            LOG.error(e)
            return False
        else:
            return True


class LocalBuilder(DockerTagger):
    
    def __call__(self, source_repo: LocalRepository, nocache=False):
        
        work_path = None
        
        try:
            LOG.info("Building image {} from repository {}".format(self.img_spec.target, source_repo))
            work_path = self.make_work_path(source_repo=source_repo)
            logs = self.docker.build(path=work_path, tag=self.img_spec.target, nocache=nocache, rm=True)
            self.print_logs(logs)
            self.image = self.docker.images(self.img_spec.target)[0]
        except Exception as e:
            raise NhaDockerError("Building {} failed".format(source_repo)) from e
        else:
            self.tag_image()
            self.push_image()
            return self.image_id
        finally:
            if work_path is not None:
                work_path.dispose()
    
    def make_work_path(self, source_repo: LocalRepository) -> Workpath:
        
        return Workpath.get_fixed(path=source_repo.path)
    
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
    
    def make_work_path(self, source_repo: GitRepository) -> Workpath:
        
        work_path = Workpath.get_tmp()
        git.Git(work_path).clone(source_repo.path)
        return work_path


def get_builder_class(source_repo: Repository):
    
    try:
        return {
            DockerRepository.__name__: DockerTagger,
            LocalRepository.__name__: LocalBuilder,
            GitRepository.__name__: GitBuilder
        }.get(source_repo.__class__.__name__)
    except KeyError:
        raise ResolutionError(
            "No builder class found for repository '{}' of type '{}'"
            .format(source_repo, source_repo.__class__.__name__)
        )
