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

"""Module for handling Docker volumes"""

import os
import pathlib
import random_name
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from noronha.bay.barrel import Barrel, DatasetBarrel, MoversBarrel
from noronha.bay.compass import MongoCompass, IslandCompass
from noronha.bay.warehouse import get_warehouse
from noronha.db.ds import Dataset
from noronha.db.main import SmartBaseDoc
from noronha.db.movers import ModelVersion
from noronha.common.conf import AllConf
from noronha.common.constants import DateFmt, OnBoard, Paths, Config, DockerConst
from noronha.common.errors import NhaStorageError


class Content(ABC):
    
    def __init__(self, file_name: str = None):
        
        self.file_name = file_name
    
    @abstractmethod
    def deploy(self, path):
        
        pass


class LiteralContent(Content):
    
    def __init__(self, file_name: str, file_content: str):
        
        super().__init__(file_name=file_name)
        self.file_content = file_content
    
    @property
    def estimate_mb(self):
        
        kb = len(self.file_content)/1024
        mb = kb/1024
        return int(mb) + 1
    
    def deploy(self, path):
        
        with open(os.path.join(path, self.file_name), 'w') as f:
            f.write(self.file_content)


class BinaryContent(Content):
    
    def __init__(self, file_name: str, file_content: bytes):
        
        super().__init__(file_name=file_name)
        self.file_content = file_content
    
    def deploy(self, path):
        
        with open(os.path.join(path, self.file_name), 'wb') as f:
            f.write(self.file_content)


class BarrelContent(Content):
    
    def __init__(self, barrel: Barrel):
        
        super().__init__(file_name=None)
        self.barrel = barrel
    
    def deploy(self, path):
        
        self.barrel.deploy(path_to=path)
    
    def get_deployables(self, path):
        
        return self.barrel.get_deployables(path_to=path)
    
    @property
    def estimate_mb(self):
        
        # TODO:
        #  implement get_estimate_mb in barrel
        #  infer by listing of repo. if compressed, multiply by 4
        if self.barrel.schema is None:
            return 1024
        else:
            return sum(fyle.max_mb or 10 for fyle in self.barrel.schema)


class Cargo(object):
    
    def __init__(self, mount_to: str, mode: str, contents: List[Content] = None, require_mb: int = 10,
                 section: str = None, alias: str = None, name: str = None, lightweight=False):
        
        if name is None:
            assert section in DockerConst.Section.ALL
            self.name = '{}-{}'.format(section, alias)
        else:
            self.name = name
        
        self.mount_to = mount_to
        self.mode = mode
        self.contents = contents
        self.require_mb = require_mb
        self.lightweight = lightweight
    
    @property
    def mount(self):
        
        return '{}:{}:{}'.format(self.name, self.mount_to, self.mode)
    
    def deploy(self, path: str = None):
        
        path = path or self.mount_to
        
        for c in self.contents:
            c.deploy(path)


class EmptyCargo(Cargo):
    
    def __init__(self, **kwargs):
        
        super().__init__(
            mode='rw',
            contents=[],
            **kwargs
        )


class MappedCargo(Cargo):
    
    def __init__(self, src: str, mode: str = 'rw', nfs: bool = False, tipe: str = 'Directory', **kwargs):
        
        self.src = src
        self.nfs = nfs
        self.tipe = tipe
        super().__init__(
            mode=mode,
            contents=[],
            **kwargs
        )
    
    @property
    def mount(self):
        
        return '{}:{}:{}'.format(self.src, self.mount_to, self.mode)


class TimezoneCargo(MappedCargo):
    
    def __init__(self, alias: str, **kwargs):
        
        super().__init__(
            src=Paths.TZ_FILE_PATH,
            alias='tz-{}'.format(alias),
            mount_to=Paths.TZ_FILE_PATH,
            mode='ro',
            tipe='File',
            **kwargs
        )


class LogsCargo(Cargo):
    
    def __init__(self, alias: str, **kwargs):
        
        super().__init__(
            mode='rw',
            contents=[],
            alias='logs-{}'.format(alias),
            mount_to=OnBoard.LOG_DIR,
            **kwargs
        )


class AnonymousCargo(Cargo):
    
    def __init__(self, **kwargs):
        
        super().__init__(
            alias='anon-{alias}-{dt}'.format(
                alias=random_name.generate_name(separator='_'),
                dt=datetime.now().strftime(DateFmt.SYSTEM)
            ),
            **kwargs
        )


class ConfCargo(Cargo):
    
    def __init__(self, alias: str, **kwargs):
        
        conf = AllConf.load().copy()
        
        compass: List[IslandCompass] = [
            MongoCompass(),
            get_warehouse(section=None).compass  # warehouse compass (artif or nexus)
        ]
        
        for comp in compass:
            comp.inject_credentials(conf)
        
        super().__init__(
            mode='ro',
            contents=[
                LiteralContent(
                    file_name=Config.FILE,
                    file_content=conf.dump()
                )
            ],
            alias='conf-{}'.format(alias),
            mount_to=OnBoard.CONF_DIR,
            **kwargs
        )


class MetaCargo(Cargo):
    
    def __init__(self, docs: List[SmartBaseDoc], alias: str = None, **kwargs):
        
        alias = alias or '-'.join([d.get_pk(delimiter='-') for d in docs])
        super().__init__(
            alias='metadata-{}'.format(alias),
            mount_to=OnBoard.META_DIR,
            mode='ro',
            contents=[
                LiteralContent(file_name=x[0], file_content=x[1])
                for x in [
                    doc.to_file_tuple()
                    for doc in docs
                ]
            ],
            **kwargs
        )
    
    def _compatible_with(self, other):
        
        return \
            isinstance(other, self.__class__) and \
            other.name == self.name and \
            other.mount_to == self.mount_to and \
            other.mode == self.mode
    
    def __add__(self, other):
        
        assert self._compatible_with(other)
        self.contents += other.contents
        return self


class HeavyCargo(Cargo):
    
    def __init__(self, barrel: Barrel, **kwargs):
        
        content = BarrelContent(barrel)
        super().__init__(require_mb=content.estimate_mb, **kwargs)
        self.contents: List[BarrelContent] = [content]
    
    def move(self, src_path):
        
        self.contents[0].barrel.move(
            path_from=src_path,
            path_to=self.mount_to
        )
    
    def get_deployables(self, path):
        
        return self.contents[0].get_deployables(path)


class DatasetCargo(HeavyCargo):
    
    def __init__(self, ds: Dataset, section: str, **kwargs):
        
        assert ds.stored, NhaStorageError(
            """Dataset '{}' is not stored by the framework, so it cannot be mounted in a container"""
            .format(ds.show())
        )
        
        subdir = ds.get_dir_name()
        dyr = OnBoard.SHARED_DATA_DIR
        super().__init__(
            alias='dataset-{}'.format(ds.get_pk()),
            mount_to=os.path.join(dyr, subdir),
            mode='ro',
            barrel=DatasetBarrel(ds, **kwargs),
            section=section,
            lightweight=ds.lightweight
        )


class MoversCargo(HeavyCargo):
    
    def __init__(self, mv: ModelVersion, section: str, local=False, **kwargs):
        
        subdir = mv.get_dir_name()
        dyr = OnBoard.LOCAL_MODEL_DIR if local else OnBoard.SHARED_MODEL_DIR
        super().__init__(
            alias='movers-{}'.format(mv.get_pk()),
            mount_to=os.path.join(dyr, subdir),
            mode='rw',
            barrel=MoversBarrel(mv, **kwargs),
            section=section,
            lightweight=mv.lightweight
        )


class SharedCargo(Cargo):
    
    def __init__(self, alias: str, cargos: List[Cargo], **kwargs):
        
        super().__init__(
            alias='shared-{}'.format(alias),
            mount_to=OnBoard.NHA_HOME,
            contents=[],
            mode='rw',
            **kwargs
        )
        
        self.subdirs = []
        self.types = []
        self.lw_flags = []
        len_prefix = len(self.mount_to) + 1
        
        for cargo in cargos:
            subdir = cargo.mount_to[len_prefix:]
            self.subdirs += [subdir]*len(cargo.contents)
            self.contents += cargo.contents
            self.types += [type(cargo)]*len(cargo.contents)
            self.lw_flags += [cargo.lightweight]*len(cargo.contents)
        
        self.estimate_mb = sum([c.estimate_mb for c in self.contents])
    
    def deploy(self, path: str = None, include_heavy_cargos=False):
        
        path = path or self.mount_to
        
        for subdir, content, tipe, lightweight in zip(self.subdirs, self.contents, self.types, self.lw_flags):
            
            if issubclass(tipe, HeavyCargo) and not include_heavy_cargos and not lightweight:
                continue
            
            subpath = os.path.join(path, subdir)
            
            if os.path.exists(subpath):
                if os.path.isfile(subpath):
                    raise IOError("Expected path '' to be a directory, not file".format(subpath))
            else:
                pathlib.Path(subpath).mkdir(parents=True, exist_ok=True)
            
            content.deploy(subpath)
    
    def get_deployables(self, path):
        
        deployables = []
        
        for subdir, content, tipe in zip(self.subdirs, self.contents, self.types):
            
            if not issubclass(tipe, HeavyCargo):
                continue
            
            assert isinstance(content, BarrelContent), NotImplementedError()
            subpath = os.path.join(path, subdir)
            deployables += content.get_deployables(subpath)
        
        return deployables
