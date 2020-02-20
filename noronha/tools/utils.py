# -*- coding: utf-8 -*-

from datetime import datetime

from noronha.bay.compass import find_cont_hostname
from noronha.common.constants import Task, DockerConst, DateFmt
from noronha.db.depl import Deployment
from noronha.db.train import Training
from noronha.db.utils import TaskDoc
from noronha.tools.shortcuts import get_purpose


class ProcMonitor(object):
    
    def __init__(self, proc):
        
        self.proc = proc.reload()
    
    @property
    def task(self):
        
        return self.proc.task
    
    @property
    def proc_name(self):
        
        return self.proc.name
    
    def set_progress(self, perc: float):
        
        if self.proc is not None:
            self.proc.reload()
            
            if perc > self.task.progress:
                self.task.progress = perc
                self.proc.save()
    
    def set_state(self, state: str):
        
        if self.proc is not None:
            self.proc.reload()
            self.task.state = state
            self.proc.save()


class MockedProcMonitor(ProcMonitor):
    
    def __init__(self, **_):
        
        self._task = TaskDoc()
        self._proc_name = datetime.now().strftime(DateFmt.SYSTEM)
    
    @property
    def proc_name(self):
        
        return self._proc_name
    
    @property
    def task(self):
        
        return self._task
    
    def set_state(self, state: str):
        
        self.task.state = state
    
    def set_progress(self, perc: float):
        
        self.task.progress = perc


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
            DockerConst.Section.IDE: (None, MockedProcMonitor),
            DockerConst.Section.TRAIN: (Training.load(ignore=True), ProcMonitor),
            DockerConst.Section.DEPL: (Deployment.load(ignore=True), MultiProcMonitor)
        }.get(get_purpose())
        
        return proc_mon_cls(proc=proc, **kwargs)
