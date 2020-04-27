from abc import ABC, abstractmethod
from flask import Flask
from flask import request as flask_req

from noronha.common.constants import Config, DateFmt, OnlineConst, Task
from noronha.common.errors import NhaDataError, PrettyError, MisusageError, ResolutionError


class SimpleApp(ABC):

    @abstractmethod
    def get_app(self):
        pass

    @abstractmethod
    def get_body(self):
        pass

    @abstractmethod
    def get_args(self):
        pass

    @abstractmethod
    def get_charset(self):
        pass

    @abstractmethod
    def _make_routes(self):
        pass


class FlaskApp(SimpleApp):

    def __init__(self, name, apis):
        self._app = Flask(name)
        self.builder = apis
        self._make_routes()

    def get_app(self):
        return self._app

    def get_body(self):
        return flask_req.get_data()

    def get_args(self):
        return flask_req.args()

    def get_charset(self):
        return flask_req.mimetype_params.get('charset') or OnlineConst.DEFAULT_CHARSET

    def _make_routes(self):
        for route, func in self.builder.items():
            assert callable(func), MisusageError("Expected a func to build app route. Got: {}".format(repr(func)))
            self._app.add_url_rule('/{}'.format(route.lower()), route.lower(), func)
