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

from typing import List

from noronha.common.logging import LOG
from noronha.db.main import SmartBaseDoc


class ListingCallback(object):

    def __init__(self, obj_title: str, expand: bool = False):
        
        self.obj_title = obj_title
        self.expand = expand
    
    def __call__(self, objs: List[SmartBaseDoc]):
        
        if len(objs) == 0:
            LOG.echo("No {}(s) found".format(self.obj_title))
        else:
            LOG.echo("Listing {}(s):".format(self.obj_title))
            
            for obj in objs:
                if self.expand:
                    LOG.echo(obj.pretty())
                else:
                    LOG.echo(obj.show())
