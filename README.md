# Noronha DataOps

This is an open source framework for hosting Machine Learning projects inside a portable, ready-to-use DataOps architecture, thus helping you benefit from the most trending DataOps practices without having to change much of your usual work behavior.

## 1) Prerequisites
* [Docker](https://docs.docker.com/install/) v17.03+ (with Swarm mode enabled)

## 2) Installation
<pre>
$ pip install git+https://github.com/athosgvag/noronha-dataops
$ nha get-me-started
</pre>

### 3) Basic usage
---
Setup your project:
<pre>
$ nha model new --name my_lstm --extension h5
$ nha proj new --name my_proj --base-image py3_default --model my_lstm --auto-host
</pre>

Dockerize it:
<pre>
$ nha tmpl docker apply -x default_project
$ nha proj build
</pre>

Get to work:
<pre>
$ nha note
</pre>

Check the [examples folder](https://github.com/athosgvag/noronha-dataops/tree/master/examples) for further steps such as training, model versioning and deploy.
