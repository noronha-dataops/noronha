# -*- coding: utf-8 -*-

import json
import warnings
from datetime import datetime
from flask import Flask, request
from werkzeug.serving import run_simple

from noronha.common.constants import DateFmt, OnlineConst
from noronha.common.errors import NhaDataError, PrettyError
from noronha.common.logging import LOG
from noronha.common.utils import assert_json
from noronha.db.depl import Deployment


class HealthCheck(object):

    _STATUS_TABLE = {
        True:  ({"status": "ok"}, OnlineConst.ReturnCode.OK),
        False: ({"status": "nok"}, OnlineConst.ReturnCode.SERVICE_UNAVAILABLE)
    }
    
    def __init__(self):
        
        self._status = False
    
    @property
    def status(self):
        
        response, code = self._STATUS_TABLE[self._status]
        return json.dumps(response), code
    
    @status.setter
    def status(self, status):
        
        assert status in self._STATUS_TABLE
        self._status = status


class OnlinePredict(object):
    
    def __init__(self, predict_method):
        
        self._service = Flask(__name__)
        self._predict_method = predict_method
        self._health = HealthCheck()
        self.movers = Deployment().load(ignore=True).movers
        
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
            response['result'] = self._predict_method(decoded_data)
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
            response = assert_json(response, encode=True, encoding=OnlineConst.DEFAULT_CHARSET)
            return response, code
    
    @property
    def response_metadata(self):
        
        meta = dict(datetime=datetime.now().strftime(DateFmt.READABLE))
        
        if self.movers is not None:
            meta['model_version'] = self.movers.name
        
        return meta
    
    def __call__(self):
        
        self._health = True
        debug = LOG.debug_mode
        
        if not debug:
            warnings.filterwarnings('ignore')
        
        run_simple(
            hostname=OnlineConst.BINDING_HOST,
            port=OnlineConst.PORT,
            use_debugger=debug,
            application=self._service
        )
