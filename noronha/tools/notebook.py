# -*- coding: utf-8 -*-

import os
import papermill as pm
from datetime import datetime

from noronha.bay.barrel import NotebookBarrel
from noronha.common.constants import OnBoard, DateFmt, Task, Extension
from noronha.common.logging import LOG
from noronha.db.proj import Project
from noronha.tools.main import NoronhaEngine
from noronha.tools.utils import load_proc_monitor


class NotebookRunner(object):

    def __init__(self, debug=False):
        
        self.debug = debug
        self.proj = Project.load()
        self.proc_mon = load_proc_monitor()
        
        if self.debug:
            LOG.debug_mode = True
    
    @property
    def output_file_name(self):
        
        if self.proc_mon is None:
            return datetime.now().strftime(DateFmt.SYSTEM)
        else:
            return self.proc_mon.proc.name
    
    def __call__(self, note_path: str, params: dict):
        
        if self.proc_mon is not None:
            NoronhaEngine.progress_callback = lambda x: self.proc_mon.set_progress(x)
        
        kwargs = dict(
            parameters=params,
            engine_name=NoronhaEngine.alias,
            input_path=os.path.join(OnBoard.APP_HOME, note_path),
            output_path='.'.join([self.output_file_name, Extension.IPYNB])
        )
        
        try:
            LOG.debug("Papermill arguments:")
            LOG.debug(kwargs)
            self.proc_mon.set_state(Task.State.RUNNING)
            pm.execute_notebook(**kwargs)
        except Exception as e:
            LOG.error("Notebook execution failed:")
            LOG.error(e)
            self.proc_mon.set_state(Task.State.FAILED)
            return_code = 1
        else:
            LOG.info("Notebook execution succeeded!")
            self.proc_mon.set_state(Task.State.FINISHED)
            return_code = 0
        
        if return_code != 0 or self.debug:
            # TODO: convert to pdf (find a light-weight lib for that)
            NotebookBarrel(
                proj=self.proj,
                notebook=note_path,
                file_name=kwargs['output_path']
            ).store_from_path(os.getcwd())
        
        return return_code
