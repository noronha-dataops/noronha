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

from noronha.bay.anchor import LocalRepository
from noronha.bay.compass import ProjectCompass
from noronha.common.annotations import Relaxed, relax, Validation, validation
from noronha.common.constants import Regex
from noronha.common.errors import ResolutionError
from noronha.common.logging import LOG
from noronha.db.proj import Project


class ProjResolver(Relaxed):
    
    BY_NAME = 'by_name'
    BY_CWD = 'by_cwd'
    BY_HOME = 'by_home_dir'
    BY_GIT = 'by_git_repo'
    BY_DOCKER = 'by_docker_repo'
    BY_CONF = 'by_conf'
    ALL = tuple([BY_NAME, BY_CWD, BY_HOME, BY_GIT, BY_DOCKER, BY_CONF])
    
    def __call__(self, ref_to_proj: str = None, resolvers: list = (), ignore: bool = False):
        
        proj = None
        
        for res in resolvers or self.ALL:
            assert res in self.ALL
            method = getattr(self, 'resolve_{}'.format(res))
            proj = method(ref_to_proj)
            
            if proj is not None:
                LOG.info("Working project is '{}'".format(proj.name))
                LOG.debug("Project resolution method was '{}'".format(res))
                break
        else:
            message = """Could not determine working project from reference '{}'""".format(ref_to_proj)
            details = """Resolvers used: {}""".format(resolvers)
            
            if ignore:
                LOG.info(message)
                LOG.debug(details)
            else:
                raise ResolutionError(message, details)
        
        return proj
    
    def resolve_by_name(self, ref_to_proj):
        
        if ref_to_proj is None:
            return None
        else:
            return Project.find_one(name=ref_to_proj)
    
    @relax
    def resolve_by_cwd(self, _):
        
        return Project.find_one(home_dir=os.getcwd())
    
    @relax
    def resolve_by_home_dir(self, ref_to_proj):
        
        return Project.find_one(home_dir=LocalRepository(ref_to_proj).address)
    
    @relax
    def resolve_by_git_repo(self, ref_to_proj):
        
        return Project.find_one(git_repo=ref_to_proj)
    
    @relax
    def resolve_by_docker_repo(self, ref_to_proj):
        
        return Project.find_one(docker_repo=ref_to_proj)
    
    @relax
    def resolve_by_conf(self, _):
        
        return self.by_name(name=ProjectCompass().cwp)


class DefaultValidation(Validation):
    
    @classmethod
    @validation
    def dns_safe(cls, x):
        
        cls.non_empty_str(x)
        
        for word in Regex.DNS_SPECIAL.split(x):
            if len(word) == 0:
                raise ValueError("Special characters can only be used between alphanumerical strings")
            elif not Regex.ALPHANUM.match(word):
                raise ValueError("Contains invalid characters")
        
        return True
    
    @classmethod
    @validation
    def non_empty_str(cls, x):
        
        assert isinstance(x, str) and len(x) > 0, ValueError("Must be a non empty string")
        return True
    
    @classmethod
    @validation
    def list_of_dicts(cls, x):
        
        assert isinstance(x, (list, tuple)) and [isinstance(y, dict) for y in x],\
            TypeError("Expected a list of dictionaries. Got: {}".format(x))
        return True
    

def _or_none(cls, method_name):
    
    @validation
    def wrapper(self, x=None):
        if x is None:
            return True
        else:
            return getattr(self, method_name)(x)
    
    setattr(cls, method_name + '_or_none', wrapper)


_or_none(DefaultValidation, 'dns_safe')
_or_none(DefaultValidation, 'non_empty_str')
_or_none(DefaultValidation, 'list_of_dicts')
