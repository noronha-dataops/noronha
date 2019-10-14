# -*- coding: utf-8 -*-

from noronha.bay.anchor import resolve_repo
from noronha.bay.compass import ProjectCompass
from noronha.common import Regex
from noronha.common.annotations import Relaxed, relax, Validation, validation
from noronha.db.proj import Project


class ProjResolver(Relaxed):
    
    BY_NAME = 'resolve_by_name'
    BY_REPO = 'resolve_by_repo'
    BY_REMOTE = 'resolve_by_remote'
    BY_CONF = 'resolve_by_conf'
    ALL = tuple([BY_NAME, BY_REPO, BY_CONF])  # BY_REMOTE is redundant with BY_REPO
    
    def resolve_by_name(self, name):
        
        if name:
            return Project.find_one(name=name)
        else:
            return None
    
    @relax
    def resolve_by_repo(self, repo, only_remote=False):
        
        repo = resolve_repo(repo, only_remote=only_remote, implicit_local=not only_remote)
        return Project.objects(repo=str(repo))[0]
    
    @relax
    def resolve_by_remote(self, repo):
        
        return self.by_repo(repo, only_remote=True)
    
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
