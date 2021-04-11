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

import os
from typing import Type

from noronha.bay.anchor import LocalRepository
from noronha.bay.cargo import EmptyCargo
from noronha.bay.compass import IslandCompass, MongoCompass, ArtifCompass, NexusCompass, RouterCompass
from noronha.bay.expedition import LongExpedition
from noronha.bay.shipyard import LocalBuilder, ImageSpec
from noronha.common.constants import DockerConst, Package, Perspective
from noronha.common.errors import ResolutionError, MisusageError
from noronha.common.logging import LOG


class Island(LongExpedition):
    
    compass_cls: Type[IslandCompass] = None
    scallable = False
    section = DockerConst.Section.ISLE
    
    def __init__(self, **kwargs):
        
        self.isle_compass = self.compass_cls(perspective=Perspective.OFF_BOARD)
        
        self.builder = LocalBuilder(
            repo=LocalRepository(address=self.source),
            img_spec=ImageSpec.for_island(self.alias),
        )
        
        super().__init__(
            img_spec=self.builder.img_spec,
            **kwargs
        )
    
    def launch(self, tasks=1, skip_build=False, just_build=False, **_):
        
        if not just_build:
            assert self.scallable or tasks == 1, MisusageError(
                "Plugin '{}' is not scallable".format(self.alias)
            )
            
            assert self.isle_compass.native, MisusageError(
                "There is no point in setting up the plugin '{}' because it's configured in 'foreign mode'"
                .format(self.alias)
            )
        
        if not skip_build:
            self.builder.build()
        
        if not just_build:
            super().launch(tasks=tasks)
            
            if self.isle_compass.port is not None:
                LOG.info("Mapping service '{}' to port {}".format(self.make_name(), self.isle_compass.port))
    
    @property
    def alias(self):
        
        return self.isle_compass.alias
    
    @property
    def source(self):
        
        return os.path.join(Package.ISLE, self.alias)
    
    def with_alias(self, cargo_name: str):
        
        return '{}-{}'.format(cargo_name, self.alias)
    
    def make_alias(self):
        
        return self.alias
    
    def make_ports(self):
        
        mapped_port = self.isle_compass.port
        
        if mapped_port is None:
            mapping = str(self.isle_compass.ORIGINAL_PORT)
        else:
            mapping = '{}:{}'.format(mapped_port, self.isle_compass.ORIGINAL_PORT)
        
        return [mapping]


class MongoIsland(Island):
    
    compass_cls = MongoCompass
    
    def make_vols(self):
        
        return [
            EmptyCargo(
                alias=self.with_alias('data'),
                section=self.section,
                mount_to='/data/db',
                require_mb=self.isle_compass.max_mb
            )
        ]
    
    def make_cmd(self):
        
        return [
            'mongod',
            '--bind_ip',
            '0.0.0.0'
        ]


class ArtifIsland(Island):
    
    compass_cls = ArtifCompass
    
    def make_vols(self):
        
        return [
            EmptyCargo(
                alias=self.with_alias('data'),
                section=self.section,
                mount_to='/var/opt/jfrog/artifactory',
                require_mb=self.isle_compass.max_mb
            )
        ]


class NexusIsland(Island):
    
    compass_cls = NexusCompass
    
    def make_vols(self):
        
        return [
            EmptyCargo(
                alias=self.with_alias('data'),
                section=self.section,
                mount_to='/nexus-data',
                require_mb=self.isle_compass.max_mb
            )
        ]


class RouterIsland(Island):
    
    compass_cls = RouterCompass
    
    def make_vols(self):
        
        return []


def get_island(name, **kwargs) -> Island:
    
    cls_lookup = {
        'mongo': MongoIsland,
        'artif': ArtifIsland,
        'router': RouterIsland,
        'nexus': NexusIsland
    }
    
    try:
        isle_cls = cls_lookup[name]
    except KeyError:
        raise ResolutionError(
            "Could not resolve plugin by reference '{}'. Options are: {}"
            .format(name, list(cls_lookup.keys()))
        )
    else:
        return isle_cls(**kwargs)
