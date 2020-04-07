# -*- coding: utf-8 -*-

import json
import warnings
import time
from abc import ABC, abstractmethod
from datetime import datetime
from flask import Flask, request
from werkzeug.serving import run_simple

from noronha.bay.compass import LWWarehouseCompass
from noronha.common.conf import LazyConf
from noronha.common.constants import Config, DateFmt, OnlineConst, Task
from noronha.common.errors import NhaDataError, PrettyError, MisusageError, ResolutionError
from noronha.common.logging import LOG
from noronha.common.parser import assert_json, assert_str, StructCleaner
from noronha.common.utils import FsHelper
from noronha.db.depl import Deployment
from noronha.tools.shortcuts import require_movers, model_path, movers_meta
from noronha.tools.utils import load_proc_monitor, HistoryQueue


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


class ModelServer(ABC):
    
    def __init__(self, predict_func, enrich=True):

        assert callable(predict_func)
        self._service = Flask(__name__)
        self._predict_func = predict_func
        self._health = HealthCheck()
        self._enrich = enrich
        self._cleaner = StructCleaner(depth=1)
        self.proc_mon = load_proc_monitor(catch_task=True)

        @self._service.route('/predict', methods=['POST'])
        def predict():
            return self._predict_route()

        @self._service.route('/health', methods=['GET'])
        def health():
            return self._health.status
    
    def make_request_kwargs(self):
        
        body = request.get_data()
        charset = request.mimetype_params.get('charset') or OnlineConst.DEFAULT_CHARSET
        return dict(
            body=body.decode(charset, 'replace'),
            args=request.args
        )
    
    @abstractmethod
    def make_result(self, body, args):
        
        pass
    
    @abstractmethod
    def make_metadata(self, body, args):
        
        pass
    
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
            elif isinstance(e, PrettyError):
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

            return response, code

    def __call__(self):

        debug = LOG.debug_mode

        if not debug:
            warnings.filterwarnings('ignore')

        try:
            if self.proc_mon is not None:
                self.proc_mon.set_state(Task.State.FINISHED)

            run_simple(
                hostname=OnlineConst.BINDING_HOST,
                port=OnlineConst.PORT,
                use_debugger=debug,
                application=self._service
            )
        except (Exception, KeyboardInterrupt) as e:
            self.proc_mon.set_state(Task.State.FAILED)
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
    
    def __init__(self, predict_func, enrich=True):
        
        super().__init__(predict_func=predict_func, enrich=enrich)
        self.movers = Deployment.load(ignore=True).movers
    
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
            model_name='iris-clf'
        )

        server()
    """

    conf = LazyConf(namespace=Config.Namespace.LW_WAREHOUSE)
    compass_cls = LWWarehouseCompass
    
    def __init__(self, predict_func, load_model_func, model_name: str = None, max_models: int = 100):
        
        assert callable(load_model_func)
        super().__init__(predict_func=predict_func, enrich=False)
        self._load_model_func = load_model_func
        self._model_name = model_name  # TODO: if not provided, resolve by shortcut model_meta
        self._max_models = max_models
        self._loaded_models = {}
        self._model_usage = HistoryQueue(max_size=max_models)
        self.compass = self.compass_cls()
    
    def purge_least_used_model(self):
        
        least_used = self._model_usage.get()
        _ = self._loaded_models.pop(least_used)

    def purge_mover(self, version):

        _ = self._loaded_models.pop(version)
    
    def enforce_model_limit(self):
        
        while len(self._loaded_models) >= self._max_models:
            self.purge_least_used_model()
    
    def load_model(self, version):
        
        self.enforce_model_limit()
        
        try:
            path = model_path(model=self._model_name, version=version)
        except ResolutionError:
            path = require_movers(model=self._model_name, version=version)

        meta = movers_meta(model=self._model_name, version=version)  # metadata related to the model version
        
        self._loaded_models[version] = tuple([
            self._load_model_func(path, meta),  # loaded model object, respective to the model version
            movers_meta(model=self._model_name, version=version),  # metadata related to the model version
            time.time()
        ])
    
    def fetch_model(self, version):

        self.enforce_time_to_leave(version)
        
        if version not in self._loaded_models:
            self.load_model(version)
        
        self._model_usage.put(version)
        return self._loaded_models[version]
        
    def make_result(self, body, args):
        
        model_args = self.fetch_model(args['model_version'])  # tuple([model_obj, movers_meta])
        return self._predict_func(body, *model_args)
    
    def make_metadata(self, body, args):
        
        raise MisusageError(  # TODO: implement some decent metadata at least for debugging purposes
            "Inference metadata for {} is ambiguous"
            .format(self.__class__.__name__)
        )

    def enforce_time_to_leave(self, version):

        try:
            if float(time.time() - self._loaded_models[version][2]) > float(self.compass.time_to_leave):
                self.purge_mover(version)
        except KeyError:  # ignores if model version is not in memory
            pass

        try:
            path = model_path(model=self._model_name, version=version)
            helper = FsHelper(path)
            if float(time.time() - helper.get_modify_time()) > float(self.compass.time_to_leave):
                helper.delete_path()
        except ResolutionError:  # ignores if model version was never loaded
            pass
