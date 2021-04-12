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

from noronha.api.main import NoronhaAPI
from noronha.bay.island import get_island
from noronha.common.constants import IslandConst


class IslandAPI(NoronhaAPI):
    
    valid = NoronhaAPI.valid
    
    def setup(self, name: str, **kwargs):
        
        return get_island(
            name,
            resource_profile=kwargs.get('resource_profile')
        ).launch(**kwargs)
    
    def get_me_started(self, **kwargs):
        
        for name in IslandConst.ESSENTIAL:
            get_island(name).launch(**kwargs)
