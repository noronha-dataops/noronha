import multiprocessing
import warnings
from abc import ABC, abstractmethod
from gunicorn.app.base import BaseApplication
from werkzeug.serving import run_simple

from noronha.bay.compass import WebServerCompass, GunicornServerCompass
from noronha.common.conf import WebServerConf
from noronha.common.constants import Config, DateFmt, OnlineConst, Task
from noronha.common.logging import LOG
from noronha.tools.utils import load_proc_monitor, HistoryQueue


class SimpleServer(ABC):

    proc_mon = load_proc_monitor(catch_task=True)

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


class WerkzeugServer(SimpleServer):

    compass = WebServerCompass()

    def __init__(self, app):
        self.app = app

    def run_server(self):
        run_simple(
            hostname=self.compass.host,
            port=self.compass.port,
            use_debugger=True,
            application=self.app,
            threaded=True
        )


class GunicornServer(BaseApplication, SimpleServer):

    compass = GunicornServerCompass()

    def __init__(self, app):
        self.app = app
        super().__init__()

    @staticmethod
    def get_threads():
        return int(2 * multiprocessing.cpu_count())

    def get_config(self):
        return dict(
            bind='{}:{}'.format(self.compass.host, self.compass.port),
            workers=1,
            worker_class='gthread',
            threads=self.get_threads()
        )

    def load_config(self):
        for k, v in self.get_config():
            self.cfg.set(k, v)

    def run_server(self):
        self.run()

    def load(self):
        return self.app
