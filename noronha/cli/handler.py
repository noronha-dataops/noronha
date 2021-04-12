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

import sys
from types import GeneratorType

from noronha.api.main import NoronhaAPI
from noronha.api.utils import ProjResolver
from noronha.common.annotations import Interactive
from noronha.common.constants import Flag
from noronha.common.errors import PrettyError
from noronha.common.logging import LOG
from noronha.common.parser import StructCleaner


class CommandHandler(Interactive):
    
    interactive_mode: bool = False
    struct_cleaner = StructCleaner(nones=[None])
    
    @classmethod
    def run(cls, _api_cls, _method, _skip_proj_resolution: bool = False, _error_callback=None, _response_callback=None,
            **method_kwargs):
        
        code, error = 0, None
        
        try:
            api = cls.init_api(_api_cls)
            method, requires_proj = cls.fetch_method(api, _method)
            method_kwargs, ref_to_proj = cls.prepare_method_kwargs(method_kwargs)
            
            if requires_proj:
                cls.set_proj(api, ref_to_proj)
            
            response = method(**method_kwargs)
            
            if isinstance(response, GeneratorType):
                [cls.show_response(res, _response_callback) for res in response]
            else:
                cls.show_response(response, _response_callback)
        except Exception as e:
            error = e
            code = 1
            cls.show_exception(e)
        finally:
            if LOG.debug_mode and error is not None:
                raise error
            else:
                sys.exit(code)
    
    @classmethod
    def set_proj(cls, api: NoronhaAPI, ref_to_proj: str):
        
        if ref_to_proj is None:
            resolvers = [ProjResolver.BY_CWD, ProjResolver.BY_CONF]
        else:
            resolvers = [ProjResolver.BY_NAME]
        
        api.set_proj(ref_to_proj, resolvers)
    
    @classmethod
    def init_api(cls, api_cls):
        
        assert issubclass(api_cls, NoronhaAPI)
        return api_cls(
            scope=NoronhaAPI.Scope.CLI,
            interactive=cls.interactive_mode
        )
    
    @classmethod
    def fetch_method(cls, api: NoronhaAPI, method_name: str):
        
        method = getattr(api, method_name)
        requires_proj = getattr(method, Flag.PROJ, False)
        return method, requires_proj
    
    @classmethod
    def prepare_method_kwargs(cls, method_kwargs: dict):
        
        method_kwargs = cls.struct_cleaner(method_kwargs)
        ref_to_proj = method_kwargs.pop('proj', None)
        return method_kwargs, ref_to_proj
    
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
            exc = PrettyError.parse_exc(exception)
        
        if callable(callback):
            detail = callback(exception)
            LOG.info(detail)
        
        LOG.error(exc)


CMD = CommandHandler()
