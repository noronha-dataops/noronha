# -*- coding: utf-8 -*-

from abc import ABC
from typing import Type
from mongoengine import Document

from noronha.api.utils import ProjResolver, DefaultValidation
from noronha.db.main import PrettyDoc
from noronha.db.proj import Project
from noronha.common.annotations import Documented, Interactive, Projected, Scoped, Validated, validate
from noronha.common.errors import NhaAPIError
from noronha.common.logging import LOG


class NoronhaAPI(Documented, Interactive, Projected, Scoped, Validated, ABC):
    
    doc: (Type[PrettyDoc], Type[Document]) = None
    proj: Project = None
    valid = DefaultValidation
    
    class Scope(object):
        
        """Static marker that indicates where the API was called from"""
        
        PYTHON = "Directly instantiating the Python API"
        REST = "HTTP request to a REST API endpoint"
        CLI = "User input to command line interface"
    
    scope = Scope.PYTHON
    
    def set_proj(self, ref_to_proj, resolvers: list = (), ignore=False):
        
        if resolvers is None:
            LOG.warn("Skipping project resolution")
            return
        
        resolver_obj = ProjResolver()
        resolvers = resolvers or ProjResolver.ALL
        
        for resolver in resolvers:
            self.proj = getattr(resolver_obj, resolver)(ref_to_proj)  # returns None if resolution goes wrong
            
            if self.proj is not None:
                LOG.info("Working project is '{}'".format(self.proj.name))
                LOG.debug("Project resolution method was '{}'".format(resolver))
                break
        else:
            message = """Could not determine working project from reference '{}'""".format(ref_to_proj)
            details = """Resolvers used: {}""".format(resolvers)
            
            if ignore:
                LOG.warn(message)
                LOG.debug(details)
            else:
                raise NhaAPIError(message, details)
        
        return self
    
    def info(self, **kwargs):
        
        return self.doc().find_one(**kwargs).expanded()
    
    def rm(self, **kwargs):
        
        return self.doc().find_one(**kwargs).delete()
    
    def lyst(self, _filter: dict = None, **kwargs):
        
        return self.doc.objects(__raw__=_filter or {}, **kwargs)
    
    @validate(_duplicate_filter=(dict, None))
    def new(self, _replace: bool = None, _duplicate_filter=None, **kwargs):
        
        if _duplicate_filter is not None and len(self.doc.objects(**_duplicate_filter)) > 0:
            LOG.warn("{} exists".format(self.doc.__name__))
            
            if _replace is None:
                self._decide("Would you like to overwrite it?", default=True, interrupt=True)
                _replace = True
        
        return self.doc(**kwargs).save(force_insert=not _replace)
    
    def replace(self, **kwargs):
        
        return self.new(_replace=True, **kwargs)
    
    @validate(filter_kwargs=dict, update_kwargs=dict)
    def update(self, filter_kwargs, update_kwargs):
        
        return self.doc().find_one(**filter_kwargs).update(**update_kwargs)
