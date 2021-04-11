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

import getpass

from noronha.api.main import NoronhaAPI
from noronha.bay.tchest import TreasureChest
from noronha.common.annotations import validate
from noronha.db.tchest import TreasureChestDoc


class TreasureChestAPI(NoronhaAPI):
    
    doc = TreasureChestDoc
    valid = NoronhaAPI.valid
    
    def info(self, name):
        
        return super().info(name=name)
    
    def rm(self, name):
        
        return super().rm(name=name)
    
    def lyst(self, _filter: dict = None, **kwargs):
        
        return super().lyst(_filter=_filter, **kwargs)
    
    @validate(name=valid.dns_safe, details=(dict, None))
    def new(self, name: str = None, user: str = None, pswd: str = None, **kwargs):
        
        TreasureChest(name=name).set_auth(
            user=user,
            pswd=pswd
        )
        
        return super().new(
            name=name,
            owner=getpass.getuser(),
            **kwargs
        )
    
    @validate(details=(dict, None))
    def update(self, name: str = None, user: str = None, pswd: str = None, **kwargs):
        
        TreasureChest(name=name).set_auth(
            user=user,
            pswd=pswd
        )
        
        return super().update(
            filter_kwargs=dict(name=name),
            update_kwargs=kwargs
        )
