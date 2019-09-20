# -*- coding: utf-8 -*-

from typing import List

from noronha.common.logging import LOG
from noronha.db.main import SmartDoc


class ListingCallback(object):

    def __init__(self, obj_title: str, obj_attr: str = None, expand: bool = False):
        
        self.obj_title = obj_title
        self.obj_attr = obj_attr
        self.expand = expand
    
    def __call__(self, objs: List[SmartDoc]):
        
        if len(objs) == 0:
            LOG.echo("No {}(s) found".format(self.obj_title))
        else:
            LOG.echo("Listing {}(s):".format(self.obj_title))
            
            for obj in objs:
                if self.expand:
                    LOG.echo(obj.pretty())
                elif self.obj_attr is None:
                    LOG.echo(obj)
                else:
                    LOG.echo(getattr(obj, self.obj_attr))
