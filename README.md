# Noronha DataOps

This framework hosts Machine Learning projects inside a portable, ready-to-use DataOps architecture, thus helping you benefit from DataOps practices without having to change much of your usual work behavior.

### 1) Prerequisites
To use Noronha in its most basic configuration all you need is:

- Any recent, stable Unix OS.
- [Docker v17+](<https://docs.docker.com/install/>) with [Swarm mode](https://docs.docker.com/engine/swarm/) enabled and [configured to be used without sudo](https://docs.docker.com/install/linux/linux-postinstall/).
- A [Conda v4.5+](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html) environment with Python v3.5+.
- [Git v2+](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

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
