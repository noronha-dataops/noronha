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
from noronha.common.annotations import projected
from noronha.common.constants import DockerConst
from noronha.db.bvers import BuildVersion


class BuildVersionAPI(NoronhaAPI):
    
    doc = BuildVersion
    valid = NoronhaAPI.valid
    
    @projected
    def info(self, tag=DockerConst.LATEST):
        
        return super().info(proj=self.proj, tag=tag)
    
    @projected
    def rm(self, tag=DockerConst.LATEST):
        
        return super().rm(proj=self.proj, tag=tag)
    
    @projected
    def lyst(self, _filter: dict = None, **kwargs):
        
        kwargs['proj'] = self.proj.name
        return super().lyst(_filter=_filter, **kwargs)
