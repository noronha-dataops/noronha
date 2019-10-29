# -*- coding: utf-8 -*-

import time
from papermill.engines import NBConvertEngine, NotebookExecutionManager
from nbformat.notebooknode import NotebookNode
from noronha.common.constants import Task
from noronha.common.logging import LOG


class ProcMonitor(object):
    
    def __init__(self, proc):
        
        self.proc = proc
    
    def set_progress(self, perc: float):
        
        if self.proc is not None:
            self.proc.reload()
            
            if perc > self.proc.task.progress:
                self.proc.task.progress = perc
                self.proc.save()
    
    def set_state(self, state: str):
        
        if self.proc is not None:
            self.proc.reload()
            
            if self.proc.task.state not in Task.State.END_STATES:
                self.proc.task.state = state
                self.proc.save()


class NoronhaNBExecManager(NotebookExecutionManager):
    
    def __init__(self, progress_callback: callable = None, **kwargs):
        
        super().__init__(**kwargs)
        self.index = 0
        self.prog = -1
        self.prog_cb = progress_callback
        assert self.prog_cb is None or callable(self.prog_cb)
    
    @classmethod
    def from_papermill_nb_man(cls, nb_man: NotebookExecutionManager, **kwargs):
        
        return cls(
            nb=nb_man.nb,
            output_path=nb_man.output_path,
            log_output=True,
            **kwargs
        )
    
    def format_source(self, cell):
        
        return 'Cell {0}:\n{1}'.format(
            self.index,
            ''.join(cell.source)
        ).strip()
    
    def echo_outputs(self, cell):
        
        if hasattr(cell, 'outputs') and len(cell.outputs) > 0:
            LOG.echo('-'*20)
            LOG.echo(
                '\n'.join([
                    node.dict().get('text', '')
                    for node in cell.outputs
                ])
            )
        
        LOG.echo('-'*20)
    
    def cell_start(self, cell, *args, **kwargs):
        
        self.index += 1
        LOG.echo(self.format_source(cell))
        super().cell_start(cell, *args, **kwargs)
    
    def cell_exception(self, cell, exception: Exception = None, *args, **kwargs):
        
        super().cell_exception(cell, exception=exception, *args, **kwargs)
        self.echo_outputs(cell)
        LOG.error(exception)
    
    def cell_complete(self, cell, *args, **kwargs):
        
        super().cell_complete(cell, *args, **kwargs)
        self.echo_outputs(cell)
        
        if self.prog_cb is not None:
            self.handle_progress()
    
    def handle_progress(self):
        
        prog = self.pbar.n/self.pbar.total
        
        if prog > self.prog:
            self.prog = prog
            self.prog_cb(prog)


class NoronhaEngine(NBConvertEngine):
    
    alias = 'noronha_engine'
    nb_man = None
    progress_callback = None
    
    @classmethod
    def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
        
        nha_nb_man = NoronhaNBExecManager.from_papermill_nb_man(
            nb_man=nb_man,
            progress_callback=cls.progress_callback
        )
        
        super().execute_managed_notebook(
            nb_man=nha_nb_man,
            kernel_name=kernel_name,
            log_output=True,
            execution_timeout=-1,
            start_timeout=-1
        )
