# -*- coding: utf-8 -*-

from noronha.bay.compass import find_cont_hostname
from noronha.common.constants import Task, DockerConst
from noronha.db.depl import Deployment
from noronha.db.train import Training
from noronha.tools.shortcuts import get_purpose


class ProcMonitor(object):
    
    def __init__(self, proc):
        
        self.proc = proc.reload()
    
    @property
    def task(self):
        
        return self.proc.task
    
    def set_progress(self, perc: float):
        
        if self.proc is not None:
            self.proc.reload()
            
            if perc > self.task.progress:
                self.task.progress = perc
                self.proc.save()
    
    def set_state(self, state: str):
        
        if self.proc is not None:
            self.proc.reload()
            
            if self.task.state not in Task.State.END_STATES:
                self.task.state = state
                self.proc.save()


class MultiProcMonitor(ProcMonitor):
    
    def __init__(self, proc, catch_task=False):
        
        self.id = find_cont_hostname()
        super().__init__(proc=proc)
        self.proc.put_task(
            task_id=self.id,
            catch_existing=catch_task
        )
        
    @property
    def task(self):
        
        return self.proc.tasks.get(self.id)


def load_proc_monitor(**kwargs):
        
        proc, proc_mon_cls = {
            DockerConst.Section.IDE: (None, None),
            DockerConst.Section.TRAIN: (Training.load(ignore=True), ProcMonitor),
            DockerConst.Section.DEPL: (Deployment.load(ignore=True), MultiProcMonitor)
        }.get(get_purpose())
        
        if proc is None:
            return None
        else:
            return proc_mon_cls(proc, **kwargs)
