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

from papermill.engines import NBClientEngine, NotebookExecutionManager
from noronha.common.constants import NoteConst
from noronha.common.logging import LOG


class NoronhaNBExecManager(NotebookExecutionManager):
    
    LINE_WIDTH = 18
    
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
    
    def _print_cell_output(self, out):
        
        dyct = out.dict()
        
        if dyct.get('output_type') == 'error':
            ename, evalue = dyct.get('ename', ''), dyct.get('evalue', '')
            LOG.error('{}: {}'.format(ename, evalue))
        else:
            text = dyct.get('text', '')
            LOG.echo(text.strip())
    
    def echo_outputs(self, cell):
        
        LOG.echo('-'*self.LINE_WIDTH)
        
        if not hasattr(cell, 'outputs') or len(cell.outputs) == 0:
            return
        
        [self._print_cell_output(out) for out in cell.outputs]
        LOG.echo('-'*self.LINE_WIDTH)
    
    def cell_start(self, cell, *args, **kwargs):
        
        self.index += 1
        LOG.echo(self.format_source(cell))
        super().cell_start(cell, *args, **kwargs)
    
    def cell_exception(self, cell, exception: Exception = None, *args, **kwargs):
        
        super().cell_exception(cell, exception=exception, *args, **kwargs)
        raise exception
    
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


class NoronhaEngine(NBClientEngine):
    
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
            start_timeout=NoteConst.START_TIMEOUT
        )
        
        nb_man.nb = nha_nb_man.nb
