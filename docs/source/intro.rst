******************
Introduction
******************

What's this?
===============

Noronnha is a framework that hosts Machine Learning projects inside a portable, ready-to-use DataOps architecture. The goal here is to help Data Scientists benefit from DataOps practices without having to change much of their usual work behavior.

Pre-requisites
===============

To use Noronha in its most basic configuration all you need is:

    - Any recent, stable Unix OS.
    - `Docker v17+ <https://docs.docker.com/install/>`_ installed with `Swarm mode <https://docs.docker.com/engine/swarm/>`_ enabled.
    - A `Conda v4.5+ <https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html>`_ environment with Python v3.5+.
    - `Git v2+ <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_.

For a more advanced usage of the framework, see the :ref:`configuration guide <configuration-guide>`.

Installation
===============

.. _installation-intro:

You can easily install Noronha by activating your Conda environment and running the following commands:

.. parsed-literal::

    pip install git+https://gitlab.eva.bot/asseteva/noronha-dataops
   
    nha get-me-started

This assumes you're going to use the default plugins (MongoDB and Artifactory) in native mode (auto-generated instances). To use plugins differently, see the :ref:`configuration guide <configuration-guide>`.

Basic usage
===============
Setup your project:

.. parsed-literal::

    nha model new --name my-lstm --model-file '{"name": "lstm.h5", "required": true}'

    nha proj new --name my-proj --model my-lstm --repo docker://user/image
   
    # OBS: repository user/image should use noronha.everis.ai/noronha as its base image

Get to work:

.. parsed-literal::

    nha note
