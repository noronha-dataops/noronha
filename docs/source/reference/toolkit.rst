************************
Python Toolkit Reference
************************

This section describes the usage of Noronha's toolkit, which is packed with the `base image <LINK TO DOCKERHUB>`_ and meant to be used in any Jupyter Notebook inside your project. The goal of the toolkit is to provide a standard way of performing some common tasks when developing and testing your training and prediction notebooks. This kind of practice can make your notebooks more generic and reusable.

Shortcuts
=========
Reference for functions inside the `shortcuts module <https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/noronha/tools/shortcuts.py>`_.

.. autofunction:: noronha.tools.shortcuts.data_path

.. autofunction:: noronha.tools.shortcuts.model_path

.. autofunction:: noronha.tools.shortcuts.dataset_meta

.. autofunction:: noronha.tools.shortcuts.movers_meta

.. autofunction:: noronha.tools.shortcuts.require_dataset

.. autofunction:: noronha.tools.shortcuts.require_movers

Publish
=======
Reference for the model publisher, which can be found in the `publish module <https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/noronha/tools/publish.py>`_.

.. autoclass:: noronha.tools.publish.Publisher

Serving
=======
Reference for the inference servers, which can be found in the `serving module <https://gitlab.eva.bot/asseteva/noronha-dataops/blob/master/noronha/tools/serving.py>`_.

.. autoclass:: noronha.tools.serving.OnlinePredict

.. autoclass:: noronha.tools.serving.LazyModelServer
