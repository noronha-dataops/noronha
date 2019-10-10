
var express = require('express');
var request = require('request');

var app = express();
app.use(express.json());

const serv_port = 8080;
const serv_endpoint = 'predict';
const syntax = {project: 'project_name', deploy: 'deploy_name', data: 'predict_input'}
const syntax_err = 'WRONG_SYNTAX'


function routerError(service, err, res) {
    
    if (err.errno == 'ENOTFOUND') {
        var code = 404;
        var message = `No such service: ${service}`;
    } else if (err.errno == syntax_err) {
        var code = 500;
        var message = {'Expected': syntax};
    } else {
        code = 501;
        message = err.message;
    }
    
    res.status(code).send({router_error: message});
}


function getServiceHost(body, res) {
    
    var project = body.project
    var deploy = body.deploy
    var data = body.data;
    
    if (project && deploy && data) {
        return `nha-depl-${project}-${deploy}`;
    } else {
        routerError(null, {errno: syntax_err}, res);
    }
}


app.post('/', (req, cli_res) => {
    
    var serv_host = getServiceHost(req.body, cli_res);

    request.post({
        url:     `http:\/\/${serv_host}:${serv_port}/${serv_endpoint}`,
        body:    JSON.stringify(req.body.data)
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
