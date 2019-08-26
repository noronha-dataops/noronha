# Noronha DataOps

This framework hosts Machine Learning projects inside a portable, ready-to-use DataOps architecture, thus helping you benefit from DataOps practices without having to change much of your usual work behavior.

### 1) Prerequisites
To use Noronha in its most basic configuration all you need to have is [Docker v17+](https://docs.docker.com/install/) with [Swarm mode](https://docs.docker.com/engine/swarm/) enabled and a [Conda v4.5+](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html) environment for installing it.

### 2) Basic installation
<pre>
$ pip install git+https://gitlab.eva.bot/asseteva/noronha-dataops
$ nha get-me-started
</pre>

### 3) Basic usage
Setup your project:
<pre>
$ nha model new --name my-lstm --model-file '{"name": "lstm.h5", "required": true}'

$ nha proj new --name my-proj --model my-lstm --repo docker://user/image

# obs: repository user/image uses noronha.everis.ai/noronha as base image 
</pre>

Get to work:
<pre>
$ nha note
</pre>

Check the [examples folder](https://github.com/athosgvag/noronha-dataops/tree/master/examples) for further steps such as training, model versioning and deploy.
