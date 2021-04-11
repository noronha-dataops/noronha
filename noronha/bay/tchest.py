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
