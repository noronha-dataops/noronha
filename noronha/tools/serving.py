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

import json
from abc import ABC, abstractmethod
from datetime import datetime

from noronha.bay.goods import build_app
from noronha.bay.trader import build_server
from noronha.common.constants import DateFmt, OnlineConst
from noronha.common.errors import NhaDataError, PrettyError, MisusageError, ResolutionError, ServingError
from noronha.common.logging import LOG
from noronha.common.parser import assert_json, assert_str, StructCleaner, join_dicts
from noronha.common.utils import FsHelper
from noronha.db.depl import Deployment
from noronha.tools.shortcuts import require_movers, model_path, movers_meta
from noronha.tools.utils import HistoryQueue


class HealthCheck(object):

    _STATUS_TABLE = {
        True:  ({"status": "ok"}, OnlineConst.ReturnCode.OK),
        False: ({"status": "nok"}, OnlineConst.ReturnCode.SERVICE_UNAVAILABLE)
    }
    
    def __init__(self):
        
        self._status = True
    
    @property
    def status(self):
        
        response, code = self._STATUS_TABLE[self._status]
        return json.dumps(response), code
    
    @status.setter
    def status(self, status):
        
        assert status in self._STATUS_TABLE
        self._status = status

    def status_route(self):

        return self.status


class ModelServer(ABC):

    def __init__(self, predict_func, enrich=True, server_conf: dict = None, server_type=None):

        if server_conf:
            assert type(server_conf) is dict, MisusageError("Server conf should be dict, but is: {}".format(type(server_conf)))

        self._predict_func = predict_func
        self._enrich = enrich
        self._health = HealthCheck()
        self._cleaner = StructCleaner(depth=1)
        self.application = build_app(__name__, self.get_routes())
        self.server = build_server(app=self.application.get_app(), server_conf=server_conf, server_type=server_type)

    @abstractmethod
    def make_result(self, body, args):

        pass

    @abstractmethod
    def make_metadata(self, body, args):

        pass

    @abstractmethod
    def get_routes(self):

        return dict(
            predict=dict(
                func=self._predict_route,
                methods=['POST']),
            health=dict(
                func=self._health.status_route,
                methods=['GET'])
        )

    def make_request_kwargs(self):

        return dict(
            body=self.application.get_body(),
            args=self.application.get_args()
        )

    def _predict_route(self):

        out, err, code = {}, None, None
        kwargs = self.make_request_kwargs()

        try:
            out = self.make_result(**kwargs)
            code = OnlineConst.ReturnCode.OK
        except Exception as e:
            if isinstance(e, NhaDataError):
                err = e.pretty()
                code = OnlineConst.ReturnCode.BAD_REQUEST
            elif isinstance(e, (PrettyError, ServingError)):
                err = e.pretty()
                code = OnlineConst.ReturnCode.SERVER_ERROR
                self._health = False
            else:
                err = repr(e)
                code = OnlineConst.ReturnCode.NOT_IMPLEMENTED

            LOG.error(err)
        finally:
            if self._enrich:
                response = self._cleaner({
                    'result': out,
                    'err': err,
                    'metadata': self.make_metadata(**kwargs)
                })
            else:
                response = out or err

            if isinstance(response, (dict, list)):
                response = assert_json(response, encode=True, encoding=OnlineConst.DEFAULT_CHARSET)
            else:
                response = assert_str(response)

            return self.application.make_response(code, response)

    def __call__(self):

        try:
            self.server()
        except (Exception, KeyboardInterrupt) as e:
            raise e


class OnlinePredict(ModelServer):

    """Utility for creating an endpoint from within a prediction notebook.

    When this class is instantiated from within a Jupyter notebook running inside
    a container managed by Noronha, it autamatically loads the metadata related to
    the project and the deployment that is running. Then, the predictor instance works as
    a function for starting the endpoint and listening for prediction requests.

    :param predict_func: Any function that receives a request's body (str), applies the predictive model and returns the prediction's result.
    :param enrich: If True, instead of returning the raw response of the prediction function the endpoint is going to return a JSON object with the prediction result and other metatada such as the prediction's datetime and the model versions used in this deployment.

    :Example:

    .. parsed-literal::
        clf = pickle.load(open('clf.pkl', 'rb'))

        def pred(x):
            data = json.loads(x)
            return clf.predict(data)

        server = OnlinePredict(
            predict_func=pred
        )

        server()
    """

    def __init__(self, predict_func, enrich=True, server_conf: dict = None, server_type=None):

        self.movers = Deployment.load(ignore=True).movers
        super().__init__(predict_func=predict_func, enrich=enrich, server_conf=server_conf, server_type=server_type)

    def get_routes(self):

        return super().get_routes()

    def make_result(self, body, args):

        return self._predict_func(body)

    def make_metadata(self, body, args):

        return self._cleaner({
            'datetime': datetime.now().strftime(DateFmt.READABLE),
            'model_version': sorted([mv.show() for mv in self.movers])
        })


class LazyModelServer(ModelServer):

    """Same as the OnlinePredict utility, but performs lazy model loading.

        When the server receives a request, the URL argument "model_version" is used
        to identify which model version is going to be employed by the prediction function.
        If that specific version is not loaded yet, then the load function is used to load it.
        If the version's files are not present in the container, then they will
        be deployed on demand with the aid of the "require_movers" shortcut.

        :param predict_func: A function that receives a request's body (str), a loaded model (object) and a model's metadata (dict), in this exact order. The function should apply the predictive model and return the prediction's result.
        :param load_model_func: A function that receives a path to a directory containing the model version's files. The function should load the model files and return an object (e.g.: a ready-to-use predictor).
        :param model_name: Name of the parent model. All model versions that are going to be served should be children to this model.
        :param max_models: Maximum number of coexisting model versions loaded in memory. If this number is reached, least used versions are going to be purged for memory optimization.
        :param server_conf: Dictionary containing server-specific configuration. This requires deep understanding of the WebServer of your choice.
        :param server_type: Name of the WebServer of your choice.
        :param enrich: If True, instead of returning the raw response of the prediction function the endpoint is going to return a JSON object with the prediction result and other metatada such as the prediction's datetime of this deployment.

        :Example:

        .. parsed-literal::

            def load(path):
                clf_file = open(path + 'clf.pkl', 'rb')
                return pickle.load(clf_file)

            def pred(x, clf, meta):
                data = json.loads(x)
                return clf.predict(data)

            server = LazyModelServer(
                predict_func=pred,
                load_model_func=load,
                model_name='iris-clf',
                server_type='gunicorn'
                server_conf=dict(timeout=300, threads=12)
            )

            server()
        """

    def __init__(self, predict_func, load_model_func, model_name: str = None, max_models: int = 100,
                 server_conf: dict = None, server_type=None, enrich=True):

        assert callable(load_model_func), MisusageError("Expected load_model_func to be callable")
        super().__init__(predict_func=predict_func, enrich=enrich, server_conf=server_conf, server_type=server_type)
        self._load_model_func = load_model_func
        self._model_name = model_name or movers_meta().model.name
        self._max_models = max_models
        self._loaded_models = {}
        self._model_usage = HistoryQueue(max_size=max_models)

    def get_routes(self):

        new_routes = dict(
            update=dict(
                func=self._update_route,
                methods=['POST']
            )
        )

        return join_dicts(super().get_routes(), new_routes)

    def delete_mover(self, version):

        try:
            _ = self._loaded_models.pop(version)
        except KeyError:  # ignores if model version was never loaded
            pass

    def enforce_model_limit(self):

        while len(self._loaded_models) >= self._max_models:
            least_used = self._model_usage.get()
            self.delete_mover(least_used)

    def load_model(self, version):

        self.enforce_model_limit()

        try:
            path = model_path(model=self._model_name, version=version)
        except ResolutionError:
            path = require_movers(model=self._model_name, version=version)

        meta = movers_meta(model=self._model_name, version=version)  # metadata related to the model version

        self._loaded_models[version] = tuple([
            self._load_model_func(path, meta),  # loaded model object, respective to the model version
            meta  # metadata related to the model version
        ])

    def fetch_model(self, version):

        if version not in self._loaded_models:
            self.load_model(version)

        self._model_usage.put(version)
        return self._loaded_models[version]

    def make_result(self, body, args):

        model_args = self.fetch_model(args['model_version'])  # tuple([model_obj, movers_meta])
        return self._predict_func(body, *model_args)

    def make_metadata(self, body, args):

        return self._cleaner({
            'datetime': datetime.now().strftime(DateFmt.READABLE)
        })

    def delete_model(self, version):

        try:
            path = model_path(model=self._model_name, version=version)
            helper = FsHelper(path)
            self.delete_mover(version)
            helper.delete_path()
        except ResolutionError:  # ignores if model version was never loaded
            pass

    def _update_route(self):

        kwargs = self.make_request_kwargs()

        if 'model_version' in kwargs['args']:
            self.delete_model(kwargs['args']['model_version'])
            self.fetch_model(kwargs['args']['model_version'])
            response, code = 'OK', 200
        else:
            response = 'Expected model_version argument\nGot: {}'.format(kwargs['args'].to_dict(flat=False))
            code = OnlineConst.ReturnCode.BAD_REQUEST

        return response, code
