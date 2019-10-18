# -*- coding: utf-8 -*-

import json
import keyring

from noronha.common.annotations import Lazy, ready
from noronha.common.errors import AuthenticationError
from noronha.common.constants import FrameworkConst


class TreasureChest(Lazy):
    
    _MOCK_USER = FrameworkConst.FW_NAME
    
    def __init__(self, name: str):
        
        self.name = name
        self.content = None
    
    def setup(self):
        
        try:
            self.content = keyring.get_credential(
                self.name,
                self._MOCK_USER
            )
            assert self.content is not None, ValueError("Got empty credentials.")
        except (RuntimeError, AssertionError) as e:
            raise AuthenticationError("Failed to load credentials '{}'.".format(self.name)) from e
    
    @ready
    def get_all(self):
        
        return json.loads(self.content.password)
    
    def get_user(self):
        
        return self.get_all()[0]
    
    def get_pswd(self):
        
        return self.get_all()[1]
    
    def get_token(self):
        
        return self.get_pswd()
    
    def set_auth(self, user: str, pswd: str):
        
        keyring.set_password(
            self.name,
            self._MOCK_USER,
            json.dumps([user, pswd])
        )
    
    def set_token(self, token: str):
        
        keyring.set_password(
            self.name,
            self._MOCK_USER,
            [None, token]
        )
