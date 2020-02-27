
# Example 2: Lazy (*lightweight*) model serving

This tutorial shows how to adapt the previous [iris example](https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/examples/1_iris/)
so that multiple model versions can be dynamically loaded and served from a single deployment.

Optionally, this serving architecture can also be integrated with Noronha's [lightweight storage](LINK TO DOCS TOPIC EXPLAINING LIGHTWEIGHT STORAGE)
in order to accelerate the loading of model files.

#### 1) (Optional) Configuring the lightweight store

Add the following lines to your Noronha's [configuration file](https://noronha-dataops.readthedocs.io/en/latest/use_guide/configuration.html#configuration-files):

```
lightweight_store:
  enabled: enabled
  type: cass
  native: false
  hosts: ['<your_cassandra_server>']
  port: 9042
```

#### 2) (Optional) Using lightweight model persistence

In the last cell of the [training notebook](https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/examples/1_iris/notebooks/train.ipynb),
add the flag `lightweight=True` when calling the model publisher:

<pre>```
Publisher()(
    <b>lightweight=True,</b>
    details=dict(
        params=params,
        metrics=metrics
    )
)
```</pre>

#### 3) The inference notebook

The [notebook](https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/examples/2_lazy/lw_predict.ipynb)
inside this example's folder employs Noronha's [LazyModelServer](https://noronha-dataops.readthedocs.io/en/latest/reference/toolkit.html#lazy-model-server)
by providing it with two simple functions: one for making predictions and one for loading models.

Copy it to your project's [notebooks folder](https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/examples/1_iris/notebooks/):

`cp lazy_predict.ipynb ../1_iris/notebooks/`

#### 4) Build

Now that the project's code has been modified, let's use Noronha's [build command](https://noronha-dataops.readthedocs.io/en/latest/reference/cli.html#build-command)
to repackage it into a new Docker image that is going to be used later when creating containers.

```
nha -d proj build \
--name botanics \
--from-home \
--tag lazy
```

#### 5) Train

Run a new training so that we have more than one model version in the database.

```
nha -d train new \
--name higher-gamma \
--nb notebooks/train \
--params '{"gamma": 0.2, "kernel": "poly"}' \
--dataset iris-clf:iris-data-v0
```

#### 6) Deploy

Create a deployment that uses the newly built Docker image to create containers
without replication and execute the new inference notebook. 

```
nha ${flags} depl new \
--name homolog \
--tag lazy \
--nb notebooks/lazy_predict \
--port 30051
```

Note that no model versions were included in the deployment's creation.
Also, the chosen Docker tag is `lazy`, the same we just built in the previous step.

#### 7) Test

Test your API with direct calls to the service:

<pre>```
<b># inference with model version "experiment-v1"</b>
curl -X POST \
--data '[1,2,3,4]' \
http://127.0.0.1:30051/predict?model_version=experiment-v1 \
&& echo

<b># inference with model version "higher-gamma"</b>
curl -X POST \
--data '[1,2,3,4]' \
http://127.0.0.1:30051/predict?model_version=higher-gamma \
&& echo
```</pre>

Test your API with a call that goes through the model router:

<pre>```
<b># inference with model version "experiment-v1"</b>
curl -X POST \
-H 'Content-Type: application/JSON' \
--data '[1,2,3,4]' \
"http://127.0.0.1:30080/predict?project=botanics&<b>deploy=lazy&model_version=experiment-v1</b>"

<b># inference with model version "higher-gamma"</b>
curl -X POST \
-H 'Content-Type: application/JSON' \
--data '[1,2,3,4]' \
"http://127.0.0.1:30080/predict?project=botanics&<b>deploy=lazy&model_version=higher-gamma</b>"
```</pre>
