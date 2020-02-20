# -*- coding: utf-8 -*-

import json
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from flask import Flask, request
from werkzeug.serving import run_simple

from noronha.common.constants import DateFmt, OnlineConst, Task
from noronha.common.errors import NhaDataError, PrettyError, MisusageError, ResolutionError
from noronha.common.logging import LOG
from noronha.common.parser import assert_json, assert_str, StructCleaner
from noronha.db.depl import Deployment
from noronha.tools.shortcuts import require_movers, model_path
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
    
    :param predict_func: Any function that receives request's body (str), applies the predictive model and returns the prediction's result.
    :param enrich: If True, instead of returning the raw response of the prediction function the endpoint is going to return a JSON object with the prediction result and other metatada such as the prediction's datetime and the model versions used in this deployment.
    
    :Example:
    
    .. parsed-literal::
        model = pickle.load(open('clf.pkl', 'rb'))
        
        def func(x):
            return model.predict(x)
        
        predict = OnlinePredict(
            predict_method=func
        )
        
        predict()
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
    
    def __init__(self, predict_func, load_model_func, model_name: str = None, max_models: int = 100):
        
        assert callable(load_model_func)
        super().__init__(predict_func=predict_func, enrich=False)
        self._load_model_func = load_model_func
        self._model_name = model_name  # TODO: if not provided, resolve by shortcut model_meta
        self._max_models = max_models
        self._loaded_models = {}
        self._model_usage = HistoryQueue(max_size=max_models)
    
    def purge_least_used_model(self):
        
        least_used = self._model_usage.get()
        _ = self._loaded_models.pop(least_used)
    
    def enforce_model_limit(self):
        
        while len(self._loaded_models) >= self._max_models:
            self.purge_least_used_model()
    
    def load_model(self, version):
        
        self.enforce_model_limit()
        
        try:
            path = model_path(model=self._model_name, version=version)
        except ResolutionError:
            path = require_movers(model=self._model_name, version=version)
        
        self._loaded_models[version] = self._load_model_func(path)
    
    def fetch_model(self, version):
        
        if version not in self._loaded_models:
            self.load_model(version)
        
        self._model_usage.put(version)
        return self._loaded_models[version]
        
    def make_result(self, body, args):
        
        model = self.fetch_model(args['model_version'])
        return self._predict_func(body, model)
    
    def make_metadata(self, body, args):
        
        raise MisusageError(
            "Inference metadata for {} is ambiguous"
            .format(self.__class__.__name__)
        )
