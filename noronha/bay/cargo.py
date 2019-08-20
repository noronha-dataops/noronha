# -*- coding: utf-8 -*-

"""Module for handling Docker volumes"""

import os
import random_name
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from noronha.bay.barrel import Barrel, DatasetBarrel, MoversBarrel
from noronha.db.ds import Dataset
from noronha.db.main import PrettyDoc
from noronha.db.movers import ModelVersion
from noronha.common.constants import DateFmt, OnBoard, Paths, Config, HostUser


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


class RemoteContent(Content):
    
    def __init__(self, file_name: str, file_url: str):
        
        super().__init__(file_name=file_name)
        self.file_url = file_url
    
    def deploy(self, path):
        
        pass  # TODO: download from file_url to os.path.join(path, self.file_name)


class BarrelContent(Content):
    
    def __init__(self, barrel: Barrel):
        
        super().__init__(file_name=None)
        self.barrel = barrel
    
    def deploy(self, path):
        
        self.barrel.deploy(path_to=path)
    
    @property
    def estimate_mb(self):
        
        return sum(fyle.max_mb or 10 for fyle in self.barrel.schema)


class Cargo(object):
    
    write_once = True
    
    def __init__(self, name, mount_to: str, mode: str, contents: List[Content] = None, require_mb: int = 10):
        
        self.name = name
        self.mount_to = mount_to
        self.mode = mode
        self.contents = contents
        self.prefix = ''
        self.require_mb = require_mb
    
    @property
    def mount(self):
        
        return '{}:{}:{}'.format(self.full_name, self.mount_to, self.mode)
    
    @property
    def full_name(self):
        
        return '{}-{}'.format(self.prefix, self.name).lstrip('-')
    
    def deploy(self, path):
        
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
    
    def __init__(self, src: str, **kwargs):
        
        self.src = src
        super().__init__(
            mode='rw',
            contents=[],
            **kwargs
        )


class TimezoneCargo(Cargo):
    
    # TODO: this class will not be used for now because mounting a volume directly to /etc is forbidden
    #  an implementation of docker secrets should do the job instead, by allowing to inject a file without
    #  replacing a whole directory. The secrets handling module could be called 'bottle'
    
    def __init__(self, suffix: str):
        
        super().__init__(
            mode='ro',
            contents=[
                BinaryContent(
                    file_name=Paths.TZ_FILE_NAME,
                    file_content=open(Paths.TZ_FILE_PATH, 'rb').read()
                )
            ],
            name='tz-{}'.format(suffix),
            mount_to=Paths.ETC
        )


class LogsCargo(Cargo):
    
    def __init__(self, suffix: str):
        
        super().__init__(
            mode='rw',
            contents=[],
            name='logs-{}'.format(suffix),
            mount_to=OnBoard.LOG_DIR
        )


class AnonymousCargo(Cargo):
    
    def __init__(self, **kwargs):
        
        super().__init__(
            name='anon-{alias}-{dt}'.format(
                alias=random_name.generate_name(separator='_'),
                dt=datetime.now().strftime(DateFmt.SYSTEM)
            ),
            **kwargs
        )


class ConfCargo(Cargo):
    
    def __init__(self, suffix: str):
        
        super().__init__(
            mode='ro',
            contents=[
                LiteralContent(
                    file_name=Config.FILE,
                    file_content=open(HostUser.CONF).read()
                )
            ],
            name='conf-{}'.format(suffix),
            mount_to=OnBoard.CONF_DIR
        )


class MetaCargo(Cargo):
    
    def __init__(self, suffix: str, docs: List[PrettyDoc]):
        
        super().__init__(
            name='metadata-{}'.format(suffix),
            mount_to=OnBoard.META_DIR,
            mode='ro',
            contents=[
                LiteralContent(file_name=x[0], file_content=x[1])
                for x in [doc.to_file_tuple() for doc in docs]
            ]
        )


class DatasetCargo(Cargo):
    
    def __init__(self, ds: Dataset):
        
        content = BarrelContent(DatasetBarrel(ds))
        super().__init__(
            name='dataset-{}-{}'.format(ds.model.name, ds.name),
            mount_to=OnBoard.SHARED_DATA_DIR,
            mode='ro',
            contents=[content],
            require_mb=content.estimate_mb
        )


class MoversCargo(Cargo):
    
    write_once = False  # allow movers volume to be cleared and reloaded even if movers is already deployed
    
    def __init__(self, mv: ModelVersion):
        
        content = BarrelContent(MoversBarrel(mv))
        super().__init__(
            name='movers-{}-{}'.format(mv.model.name, mv.name),
            mount_to=OnBoard.SHARED_MODEL_DIR,
            mode='rw',
            contents=[content],
            require_mb=content.estimate_mb
        )


class SharedCargo(Cargo):
    
    write_once = False  # no matter the contents, shared cargos can always be overwritten
    
    def __init__(self, name, cargos: List[Cargo]):
        
        super().__init__(
            name='shared-{}'.format(name),
            mount_to=OnBoard.NHA_HOME,
            contents=[],
            mode='rw'
        )
        
        self.subdirs = []
        len_prefix = len(self.mount_to) + 1
        
        for cargo in cargos:
            subdir = cargo.mount_to[len_prefix:]
            self.subdirs += [subdir]*len(cargo.contents)
            self.contents += cargo.contents
        
        self.estimate_mb = sum([c.estimate_mb for c in self.contents])
    
    def deploy(self, path):
        
        for subdir, content in zip(self.subdirs, self.contents):
            subpath = os.path.join(path, subdir)
            
            if os.path.exists(subpath):
                if os.path.isfile(subpath):
                    raise IOError("Expected path '' to be a directory, not file".format(subpath))
            else:
                os.mkdir(subpath)
            
            content.deploy(subpath)
