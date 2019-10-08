# -*- coding: utf-8 -*-

import git
import os
from abc import ABC

from noronha.common.constants import RepoConst, DockerConst
from noronha.common.errors import ResolutionError


class Protocol(object):
    
    def __init__(self, prefix):
        
        self.prefix = prefix
    
    def test(self, address):
        
        return address.startswith(self.prefix)
    
    def get_path(self, address):
        
        return address[len(self.prefix):]


class Repository(ABC):
    
    _protocol = None
    remote = True
    
    @property
    def git_hash(self):
        
        return None
    
    @property
    def protocol(self):
        
        return self._protocol
    
    @protocol.setter
    def protocol(self, protocol):
        
        assert isinstance(protocol, Protocol)
        self._protocol = protocol
    
    def __init__(self, address):
        
        assert self.protocol.test(address),\
            "Not a valid {}: {}".format(self.__class__.__name__, address)
        self.address = address
    
    @property
    def path(self):
        
        return self.protocol.get_path(self.address)
    
    def __str__(self):
        
        return self.address


class LocalRepository(Repository):
    
    _protocol = Protocol(prefix=RepoConst.ProtoPrefix.LOCAL)
    remote = False
    
    def __init__(self, address):
        
        super().__init__(address)
        path = self.protocol.get_path(address)
        assert os.path.isdir(path)
        self.address = self.protocol.prefix + os.path.abspath(path)
    
    @property
    def git_repo(self):
        
        return git.Repo(self.path)
    
    @property
    def git_hash(self):
        
        try:
            return str(self.git_repo.head.commit)
        except git.exc.InvalidGitRepositoryError:
            return None


class GitRepository(Repository):
    
    _protocol = Protocol(prefix=RepoConst.ProtoPrefix.GIT)
    
    @property
    def git_hash(self):  # DISCLAIMER: always assumes the master branch is being used
        
        cmd = 'git ls-remote --heads {}'.format(self.path).split(' ')
        return git.Git(os.getcwd()).execute(cmd).split('\n')[0].split('\t')[0]


class DockerRepository(Repository):
    
    _protocol = Protocol(prefix=RepoConst.ProtoPrefix.DOCKER)
    
    @property
    def full_repo_name(self):
        
        return self.path.split(':')[0]  # <docker_user>/<registry_repository>
    
    @property
    def tag(self):
        
        try:
            return self.path.split(':')[1]
        except IndexError:
            return DockerConst.LATEST


REPO_TYPES = tuple([LocalRepository, GitRepository, DockerRepository])


def resolve_repo(address, repo_options=(), implicit_local=False, only_remote=False):
    
    repo_options = repo_options or REPO_TYPES
    assert isinstance(repo_options, (list, tuple)),\
        "Expected list or tuple of Repository types. Got: {}".format(repo_options)
    
    for repo_type in repo_options:
        assert issubclass(repo_type, Repository)
        
        try:
            repo_obj = repo_type(address)
            
            if only_remote:
                assert repo_obj.remote, ResolutionError("Expected a remote repository, not local")
            
            return repo_obj
        except AssertionError:
            continue
    else:
        if implicit_local and os.path.exists(address):
            return LocalRepository(RepoConst.ProtoPrefix.LOCAL + os.path.abspath(address))
        else:
            raise ResolutionError(
                "Could not resolve repository type by address '{}'".format(address),
                "Options tried: {}".format([op.__name__ for op in repo_options])
            )
