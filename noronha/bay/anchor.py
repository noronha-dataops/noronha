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

import git
import os
from abc import ABC

from noronha.common.constants import DockerConst
from noronha.common.errors import ResolutionError
from noronha.db.proj import Project


class Repository(ABC):
    
    remote: bool = None
    builds_from: str = None
    
    def __init__(self, address: str):
        
        assert isinstance(address, str) and len(address) > 0,\
            ResolutionError("Cannot instantiate {} from reference {}".format(self.__class__.__name__, address))
        
        self.address = address
    
    @property
    def tipe(self):
        
        return self.__class__.__name__[:-len('Repository')]
    
    def __str__(self):
        
        return '{}:{}'.format(self.tipe, self.address)
    
    def __repr__(self):
        
        return self.__str__()
    
    @property
    def git_version(self):
        
        raise NotImplementedError()
    
    @classmethod
    def from_project(cls, proj: Project):
        
        raise NotImplementedError


class LocalRepository(Repository):
    
    remote = False
    builds_from = DockerConst.BuildSource.LOCAL
    
    def __init__(self, address: str = None):
        
        assert os.path.isdir(address)
        super().__init__(os.path.abspath(address))
    
    @classmethod
    def from_project(cls, proj: Project):
        
        return cls(proj.home_dir)
    
    @property
    def git_repo(self):
        
        return git.Repo(self.address)
    
    @property
    def git_version(self):
        
        try:
            return str(self.git_repo.head.commit)
        except git.exc.InvalidGitRepositoryError:
            return None


class GitRepository(Repository):
    
    remote = True
    builds_from = DockerConst.BuildSource.GIT
    
    @classmethod
    def from_project(cls, proj: Project):
        
        return cls(proj.git_repo)
    
    @property
    def git_version(self):
        
        # TODO: handle possibility that current branch is not master
        cmd = 'git ls-remote --heads {}'.format(self.address).split(' ')
        return git.Git(os.getcwd()).execute(cmd).split('\n')[0].split('\t')[0]
    
    @property
    def name(self):
        
        return self.address.split('/')[-1]
    
    def clone(self, path):
        
        git.Git(path).clone(self.address)


class DockerRepository(Repository):
    
    remote = True
    builds_from = DockerConst.BuildSource.PRE
    
    @property
    def git_version(self):
        
        # TODO: create container and copy .git dir from cont:/app to a tmp Workpath, get git version
        return None
    
    @classmethod
    def from_project(cls, proj: Project):
        
        return cls(proj.docker_repo)
    
    @property
    def registry(self):
        
        parts = self.address.split('/')
        
        if len(parts) == 1:
            return None
        else:
            return '/'.join(parts[:-1])
    
    @property
    def image(self):
        
        return self.address.split('/')[-1]
