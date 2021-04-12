
/*
Copyright Noronha Development Team

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

var express = require('express');
var request = require('request');

var app = express();
app.use(express.json());

const serv_port = 8080;
const serv_endpoint = 'predict';
const syntax = "/predict?project=<project_name>&deploy=<deploy_name>"
const syntax_err = 'WRONG_SYNTAX'


function routerError(service, err, res) {

    var code = null
    var message = null
    
    if (err.errno == 'ENOTFOUND') {
        code = 404;
        message = `No such service: ${service}`;
    } else if (err.errno == syntax_err) {
        code = 500;
        message = {'Expected': syntax};
    } else {
        code = 501;
        message = err.message;
    }
    
    res.status(code).send({router_error: message});
}


function getServiceHost(query, res) {
    
    var project = query.project
    var deploy = query.deploy
    
    if (project && deploy) {
        return `nha-depl-${project}-${deploy}`;
    } else {
        routerError(null, {errno: syntax_err}, res);
    }
}


app.post('/predict', (req, cli_res) => {
    
    var serv_host = getServiceHost(req.query, cli_res);
    
    request.post({
        url:     `http:\/\/${serv_host}:${serv_port}${req.url}`,
        body:    JSON.stringify(req.body)
    }, (err, res, body) => {

        if (err) {
            routerError(serv_host, err, cli_res);
        } else {
            cli_res.status(res.statusCode).send(body);
        }

    });

});


app.post('/update', (req, cli_res) => {

    var serv_host = getServiceHost(req.query, cli_res);

    request.post({
        url:     `http:\/\/${serv_host}:${serv_port}${req.url}`,
        body:    JSON.stringify(req.body)
    }, (err, res, body) => {

        if (err) {
            routerError(serv_host, err, cli_res);
        } else {
            cli_res.status(res.statusCode).send(body);
        }

    });

});


app.get('/', (req, cli_res) => {

    cli_res.status(200).send('OK')

});

app.listen(80);
