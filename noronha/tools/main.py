# -*- coding: utf-8 -*-

import time
from papermill.engines import NBConvertEngine
from threading import Thread

from noronha.common.constants import Task


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


class NoronhaEngine(NBConvertEngine):
    
    alias = 'noronha_engine'
    nb_man = None
    progress_callback = None
    
    @classmethod
    def handle_callbacks(cls):
        
        curr_prog = -1
        
        while cls.nb_man is not None:
            nb_man = cls.nb_man
            
            if callable(cls.progress_callback):
                pbar = nb_man.pbar
                
                if pbar is not None:
                    prog = pbar.n/pbar.total
                
                    if prog > curr_prog:
                        curr_prog = prog
                        cls.progress_callback(prog)
            
            time.sleep(1)
    
    @classmethod
    def execute_managed_notebook(cls, nb_man, kernel_name, **kwargs):
        
        cls.nb_man = nb_man
        t = Thread(target=cls.handle_callbacks)
        t.start()
        super().execute_managed_notebook(nb_man, kernel_name, execution_timeout=-1, start_timeout=-1)
        cls.nb_man = None
        t.join()
