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

from noronha.common.parser import StructCleaner


class PrettyError(Exception):
    
    @classmethod
    def parse_cause(cls, exc: Exception = None):
        
        if exc.__cause__ is None:
            if len(exc.args) == 1 and isinstance(exc.args[0], Exception):
                exc.__cause__ = exc.args[0]
            else:
                return None
        
        if isinstance(exc.__cause__, cls):
            return exc.__cause__.pretty()
        else:
            return '{}: {}'.format(
                exc.__cause__.__class__.__name__,
                exc.__cause__.__str__()
            )
    
    @classmethod
    def parse_exc(cls, exc: Exception = None):
        
        cause = cls.parse_cause(exc)
        
        dyct = StructCleaner()(dict(
            Error=exc.__class__.__name__,
            Message=str(exc),
            cause=cause
        ))
        
        if isinstance(cause, dict) and cause.get('Message') == dyct.get('Message'):
            _ = dyct.pop('Message', None)
        
        return dyct
    
    def pretty(self):
        
        return self.parse_exc(self)
    
    def __str__(self):
        
        return '; '.join([str(arg) for arg in self.args])


class ServingError(PrettyError):

    def pretty(self):

        dyct = super().pretty()

        for k, v in dyct.items():
            dyct.pop(k)
            dyct[k.lower()] = v

        return dyct


class DBError(PrettyError):
    
    class MultipleFound(PrettyError):
        
        pass
    
    class NotFound(PrettyError):
        
        pass


class NhaDataError(PrettyError):
    
    pass


class NhaDockerError(PrettyError):
    
    pass


class NhaAPIError(PrettyError):
    
    pass


class NhaValidationError(PrettyError):
    
    pass


class ResolutionError(PrettyError):
    
    pass


class ConfigurationError(PrettyError):
    
    pass


class AuthenticationError(PrettyError):
    
    pass


class MisusageError(PrettyError):
    
    pass


class NhaStorageError(PrettyError):

    pass


class NhaConsistencyError(PrettyError):
    
    pass


class PatientError(Exception):
    
    def __init__(self, original_exception: Exception, raise_callback=None, wait_callback=None):
        
        assert raise_callback is None or callable(raise_callback)
        assert wait_callback is None or callable(wait_callback)
        assert isinstance(original_exception, Exception)
        self._wait_callback = wait_callback
        self._raise_callback = raise_callback
        self.original_exception = original_exception
    
    def raise_callback(self):
        
        if self._raise_callback is None:
            raise self.original_exception
        else:
            self._raise_callback(self.original_exception)
    
    def wait_callback(self):
        
        if self._wait_callback is not None:
            self._wait_callback()
