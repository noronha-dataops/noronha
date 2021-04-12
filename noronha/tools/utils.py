# -*- coding: utf-8 -*-

# Copyright Noronha Development Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


class HistoryQueue(object):
    
    def __init__(self, max_size: int):
        
        self.max_size = max_size
        self.history = []
    
    @property
    def size(self):
        
        return len(self.history)
    
    def put(self, item):
        
        if self.size >= self.max_size:
            trunc_index = self.size - self.max_size + 1
            self.history = self.history[trunc_index:]
        
        if item in self.history:
            self.history.remove(item)
        
        self.history.append(item)
    
    def get(self):
        
        return self.history.pop(0)
