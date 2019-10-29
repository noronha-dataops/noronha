# -*- coding: utf-8 -*-

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
