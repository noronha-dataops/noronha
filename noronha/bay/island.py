# -*- coding: utf-8 -*-

import os
from typing import Type

from noronha.bay.anchor import LocalRepository
from noronha.bay.cargo import EmptyCargo
from noronha.bay.compass import IslandCompass, MongoCompass, ArtifCompass, NexusCompass, RouterCompass
from noronha.bay.expedition import LongExpedition
from noronha.bay.shipyard import LocalBuilder
from noronha.common.constants import DockerConst, FW_TAG, Package
from noronha.common.errors import ResolutionError, MisusageError


class Island(LongExpedition):
    
    compass_cls: Type[IslandCompass] = None
    scallable = False
    section = DockerConst.Section.ISLE
    
    def __init__(self):
        
        self.isle_compass = self.compass_cls()
        self.repo = LocalRepository(address='local://' + self.source)
        self.builder = LocalBuilder(
            target_name=self.alias,
            target_tag=FW_TAG,
            section=DockerConst.Section.ISLE
        )
        super().__init__(img_spec=self.builder.img_spec)
    
    def launch(self, tasks=1, skip_build=False, **_):
        
        assert self.scallable or tasks == 1, MisusageError(
            "Plugin '{}' is not scallable".format(self.alias)
        )
        
        assert self.isle_compass.native, MisusageError(
            "There is no point in setting up the plugin '{}' because it's configured in 'foreign mode'"
            .format(self.alias)
        )
        
        if not skip_build:
            self.builder(self.repo)
        
        super().launch(tasks=tasks)
    
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
        
        return [
            '{}:{}'.format(self.isle_compass.port, self.isle_compass.ORIGINAL_PORT)
        ]


class MongoIsland(Island):
    
    compass_cls = MongoCompass
    
    def make_vols(self):
        
        return [
            EmptyCargo(
                name=self.with_alias('data'),
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
                name=self.with_alias('data'),
                mount_to='/var/opt/jfrog/artifactory',
                require_mb=self.isle_compass.max_mb
            )
        ]


class NexusIsland(Island):
    
    compass_cls = NexusCompass
    
    def make_vols(self):
        
        return [
            EmptyCargo(
                name=self.with_alias('data'),
                mount_to='/nexus-data',
                require_mb=self.isle_compass.max_mb
            )
        ]


class RouterIsland(Island):
    
    compass_cls = RouterCompass


def get_island(name) -> Island:
    
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
        return isle_cls()
