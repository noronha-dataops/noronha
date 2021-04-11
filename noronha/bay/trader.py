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

import warnings
from abc import ABC, abstractmethod
from gunicorn.app.base import BaseApplication
from werkzeug.serving import run_simple

from noronha.bay.compass import WebServerCompass, GunicornCompass
from noronha.common.constants import Task
from noronha.common.errors import ResolutionError
from noronha.common.logging import LOG
from noronha.common.parser import join_dicts
from noronha.tools.utils import load_proc_monitor


class Server(ABC):

    proc_mon = None

    @abstractmethod
    def run_server(self):

        pass

    def __call__(self):

        debug = LOG.debug_mode

        if not debug:
            warnings.filterwarnings('ignore')

        try:
            if self.proc_mon is not None:
                self.proc_mon.set_state(Task.State.FINISHED)

            self.run_server()
        except (Exception, KeyboardInterrupt) as e:
            self.proc_mon.set_state(Task.State.FAILED)
            raise e


class SimpleServer(Server):

    compass = WebServerCompass()

    def __init__(self, app, model_conf=None):

        self.app = app
        self.model_conf = model_conf or {}
        self.proc_mon = load_proc_monitor(catch_task=True)

    def enable_threads(self):

        return self.model_conf.get('threaded', self.compass.threads['enabled'])

    def enable_debug(self):

        return self.model_conf.get('use_debugger', self.compass.enable_debug)

    def run_server(self):

        run_simple(
            hostname=self.compass.host,
            port=self.compass.port,
            use_debugger=self.enable_debug(),
            application=self.app,
            threaded=self.enable_threads()
        )


class GunicornServer(BaseApplication, Server):

    compass = GunicornCompass()

    def __init__(self, app, model_conf=None):

        self.app = app
        self.model_conf = model_conf
        self.proc_mon = load_proc_monitor(catch_task=True)
        super().__init__()

    def get_config(self):

        return join_dicts(self.compass.get_extra_conf(), self.model_conf, allow_overwrite=True)

    def load_config(self):

        for k, v in self.get_config().items():
            self.cfg.set(k, v)

    def run_server(self):

        self.run()

    def load(self):

        return self.app


def build_server(app, server_conf, server_type) -> Server:

    server_compass = WebServerCompass
    server_name = server_type or server_compass().tipe.strip().lower()

    cls_lookup = {
        'simple': SimpleServer,
        'gunicorn': GunicornServer,
    }

    try:
        server_cls = cls_lookup[server_name]
    except KeyError:
        raise ResolutionError(
            "Could not resolve server by reference '{}'. Options are: {}".format(server_name, list(cls_lookup.keys()))
        )
    else:
        return server_cls(app, server_conf)
