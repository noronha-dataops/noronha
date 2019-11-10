# -*- coding: utf-8 -*-

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
