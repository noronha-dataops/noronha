# -*- coding: utf-8 -*-

import os
import sys
from types import GeneratorType

from noronha.api.main import NoronhaAPI
from noronha.api.utils import ProjResolver
from noronha.common.annotations import Interactive
from noronha.common.errors import PrettyError
from noronha.common.logging import LOG
from noronha.common.utils import StructCleaner


class CommandHandler(Interactive):
    
    @classmethod
    def run(cls, _api_cls, _method, _proj_resolvers: (list, None) = (), _error_callback=None, _response_callback=None,
            **method_kwargs):
        
        assert issubclass(_api_cls, NoronhaAPI)
        NoronhaAPI.scope = NoronhaAPI.Scope.CLI
        NoronhaAPI.interactive = cls.interactive
        method_kwargs = StructCleaner(nones=[None])(method_kwargs)
        api, code, error = None, None, None
        
        if _proj_resolvers is None:
            ref_to_proj = None
            proj_resolvers = None
        elif 'proj' in method_kwargs:
            ref_to_proj = method_kwargs.pop('proj', None)
            proj_resolvers = None if ref_to_proj == 'null' else [ProjResolver.BY_NAME]
        else:
            ref_to_proj = os.getcwd()
            proj_resolvers = _proj_resolvers or [ProjResolver.BY_REPO, ProjResolver.BY_CONF]
        
        try:
            api = _api_cls()
            api.set_proj(ref_to_proj=ref_to_proj, resolvers=proj_resolvers, ignore=True)
            response = getattr(api, _method)(**method_kwargs)
            
            if isinstance(response, GeneratorType):
                [cls.show_response(res, _response_callback) for res in response]
            else:
                cls.show_response(response, _response_callback)
        except Exception as e:
            error = e
            code = 1
            cls.show_exception(e)
        else:
            code = 0
        finally:
            if api is not None and hasattr(api, 'close'):
                api.close()
        
        if LOG.debug_mode and error is not None:
            raise error
        else:
            sys.exit(code)
    
    @classmethod
    def show_response(cls, response, callback=None):
        
        if callable(callback):
            response = callback(response)
        
        if response is not None:
            LOG.echo(response)
    
    @classmethod
    def show_exception(cls, exception, callback=None):
        
        if isinstance(exception, PrettyError):
            exc = exception.pretty()
        else:
            exc = PrettyError.pretty(self=exception)
        
        if callable(callback):
            detail = callback(exception)
            LOG.info(detail)
        
        LOG.error(exc)


CMD = CommandHandler()
