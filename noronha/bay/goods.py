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

from abc import ABC, abstractmethod
from flask import Flask
from flask import request as flask_req

from noronha.bay.compass import WebAppCompass
from noronha.common.constants import OnlineConst, WebApiConst
from noronha.common.errors import MisusageError, ResolutionError


class App(ABC):

    def __init__(self, apis):

        self._validate_apis(apis)

    @abstractmethod
    def get_app(self):

        pass

    @abstractmethod
    def get_args(self):

        pass

    @abstractmethod
    def get_body(self):

        pass

    @abstractmethod
    def get_charset(self):

        pass

    @abstractmethod
    def _make_routes(self):

        pass

    @abstractmethod
    def make_response(self, status, response):

        pass

    def _validate_apis(self, apis):

        assert isinstance(apis, dict), MisusageError("Expected dict to build app routes. Got: {}".format(type(apis)))

        for route in apis:
            func = apis[route].get('func', None)
            assert callable(func), MisusageError("Expected func to deal with route. Got: {}".format(type(func)))

            methods = apis[route].get('methods', [None])
            methods = [methods] if isinstance(methods, str) else methods
            assert all(method in WebApiConst.Methods.ALL for method in methods), \
                MisusageError("Expected api method to be in: {}. Got: {}".format(WebApiConst.Methods.ALL, methods))


class FlaskApp(App):

    def __init__(self, name, apis):
        super().__init__(apis)
        self._app = Flask(name)
        self.builder = apis
        self._make_routes()

    def get_app(self):

        return self._app

    def get_args(self):

        return flask_req.args

    def get_body(self):

        return flask_req.get_data().decode(self.get_charset(), 'replace')

    def get_charset(self):

        return flask_req.mimetype_params.get('charset') or OnlineConst.DEFAULT_CHARSET

    def make_response(self, status, response):

        return self._app.make_response((
            response,
            status,
            {'Content-Type': 'application/json', 'Charset': 'utf-8'}
        ))

    def _make_routes(self):

        for route in self.builder:
            self._app.add_url_rule(
                rule='/{}'.format(route),
                view_func=self.builder[route]['func'],
                methods=self.builder[route]['methods'])


def build_app(name, apis) -> App:

    app_compass = WebAppCompass
    app_type = app_compass().tipe.strip().lower()

    cls_lookup = {
        'flask': FlaskApp,
    }

    try:
        app_cls = cls_lookup[app_type]
    except KeyError:
        raise ResolutionError(
            "Could not resolve app by reference '{}'. Options are: {}".format(app_type, list(cls_lookup.keys()))
        )
    else:
        return app_cls(name, apis)
