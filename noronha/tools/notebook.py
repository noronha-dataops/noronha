# -*- coding: utf-8 -*-

import os
import papermill as pm
from datetime import datetime
from papermill.exceptions import PapermillExecutionError

from noronha.bay.barrel import NotebookBarrel
from noronha.common.constants import OnBoard, DateFmt, Task, Extension, DockerConst
from noronha.common.logging import LOG
from noronha.db.proj import Project
from noronha.db.depl import Deployment
from noronha.db.train import Training
from noronha.tools.main import NoronhaEngine, ProcMonitor
from noronha.tools.shortcuts import get_purpose


class NotebookRunner(ProcMonitor):

    def __init__(self, debug=False):
        
        self.debug = debug
        self.proj = Project.load()
        super().__init__(proc=self._find_proc())
        
        if self.debug:
            LOG.debug_mode = True
    
    def _find_proc(self):
        
        return {
            DockerConst.Section.IDE: None,
            DockerConst.Section.TRAIN: Training.load(ignore=True),
            DockerConst.Section.DEPL: Deployment.load(ignore=True)
        }.get(get_purpose())
    
    @property
    def output_file_name(self):
        
        if self.proc is None:
            return datetime.now().strftime(DateFmt.SYSTEM)
        else:
            return self.proc.name
    
    def __call__(self, note_path: str, params: dict):

        if self.proc is not None:
            NoronhaEngine.progress_callback = lambda x: self.set_progress(x)
        
        kwargs = dict(
            parameters=params,
            engine_name=NoronhaEngine.alias,
            input_path=os.path.join(OnBoard.APP_HOME, note_path),
            output_path='.'.join([self.output_file_name, Extension.IPYNB])
        )
        
        try:
            LOG.debug("Papermill arguments:")
            LOG.debug(kwargs)
            self.set_state(Task.State.RUNNING)
            pm.execute_notebook(**kwargs)
        except (PapermillExecutionError, KeyError, AttributeError) as e:
            LOG.error("Notebook execution failed:")
            LOG.error(e)
            self.set_state(Task.State.FAILED)
            return_code = 1
        else:
            LOG.info("Notebook execution succeeded!")
            self.set_state(Task.State.FINISHED)
            return_code = 0
        
        if return_code != 0 or self.debug:
            # TODO: convert to pdf (find a light-weight lib for that)
            NotebookBarrel(
                proj=self.proj,
                notebook=note_path,
                file_name=kwargs['output_path']
            ).store_from_path(os.getcwd())
        
        return return_code
