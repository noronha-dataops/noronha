# -*- coding: utf-8 -*-

import json
import warnings
from datetime import datetime
from flask import Flask, request
from werkzeug.serving import run_simple

from noronha.common.constants import DateFmt, OnlineConst, Task
from noronha.common.errors import NhaDataError, PrettyError
from noronha.common.logging import LOG
from noronha.common.parser import assert_json, assert_str
from noronha.db.depl import Deployment
from noronha.tools.utils import load_proc_monitor


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


class OnlinePredict(object):
    
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
        
        self._service = Flask(__name__)
        self._predict_func = predict_func
        self._health = HealthCheck()
        self._enrich = enrich
        self.movers = Deployment.load(ignore=True).movers
        self.proc_mon = load_proc_monitor(catch_task=True)
        
        @self._service.route('/predict', methods=['POST'])
        def predict():
            return self._predict_route()
        
        @self._service.route('/health', methods=['GET'])
        def health():
            return self._health.status
    
    def _predict_route(self):
        
        response, code, e = {}, None, None
        
        try:
            data = request.get_data()
            charset = request.mimetype_params.get('charset') or OnlineConst.DEFAULT_CHARSET
            decoded_data = data.decode(charset, 'replace')
            response['result'] = self._predict_func(decoded_data)
            response['metadata'] = self.response_metadata
            code = OnlineConst.ReturnCode.OK
        except Exception as e:
            if isinstance(e, NhaDataError):
                response['exception'] = e.pretty()
                code = OnlineConst.ReturnCode.BAD_REQUEST
            elif isinstance(e, PrettyError):
                response['exception'] = e.pretty()
                code = OnlineConst.ReturnCode.SERVER_ERROR
                self._health = False
            else:
                response['exception'] = repr(e)
                code = OnlineConst.ReturnCode.NOT_IMPLEMENTED
            
            LOG.error(response)
        finally:
            if not self._enrich:
                response = response.get('exception') or response.get('result')
            
            if isinstance(response, (dict, list)):
                response = assert_json(response, encode=True, encoding=OnlineConst.DEFAULT_CHARSET)
            else:
                response = assert_str(response)
            
            return response, code
    
    @property
    def response_metadata(self):
        
        meta = dict(datetime=datetime.now().strftime(DateFmt.READABLE))
        
        if self.movers:
            meta['model_version'] = sorted([mv.show() for mv in self.movers])
        
        return meta
    
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
