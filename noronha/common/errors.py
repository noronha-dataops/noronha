# -*- coding: utf-8 -*-

from noronha.common.utils import StructCleaner


class PrettyError(Exception):
    
    def parse_cause(self):
        
        if self.__cause__ is None:
            return None
        elif isinstance(self.__cause__, self.__class__):
            return self.__cause__.pretty()
        else:
            return '{}: {}'.format(
                self.__cause__.__class__.__name__,
                self.__cause__.__str__()
            )
    
    def pretty(self):
        
        return StructCleaner()(dict(
            Error=self.__class__.__name__,
            Message=str(self),
            cause=PrettyError.parse_cause(self)
        ))
    
    def __str__(self):
        
        return '; '.join([str(arg) for arg in self.args])


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
    
    def __init__(self, wait_callback, original_exception):
        
        assert callable(wait_callback)
        assert isinstance(original_exception, Exception)
        self.wait_callback = wait_callback
        self.original_exception = original_exception
