# -*- coding: utf-8 -*-

# Copyright Noronha Development Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from noronha.api.movers import ModelVersionAPI
from noronha.bay.cargo import MoversCargo, MetaCargo
from noronha.common.constants import Paths, DockerConst
from noronha.common.errors import ResolutionError
from noronha.common.logging import LOG
from noronha.db.proj import Project
from noronha.db.train import Training
from noronha.tools.shortcuts import dataset_meta, movers_meta, get_purpose


class Publisher(object):
    
    """Utility for publishing model versions from within a training notebook.
    
    When this class is instantiated from within a Jupyter notebook running inside
    a container managed by Noronha, it autamatically loads the metadata related to
    the project and the training execution. Then, the publisher instance works as
    a function for publishing a model version.
    
    In most situations, the function's behaviour is to infer everything necessary for
    publishing the version (e.g.: which is the parent model, which dataset was used,
    which pre-trained model was used, etc).
    
    For explicity, the following parameters may be specified:
    
    :param src_path: Path to directory inside the container's temporary file system in which the model files reside.
           May also be a path to a file, if the model's persistence requires only one file.
    :param details: Dictionary with any details about the model version (may be nested).
    :param version_name: Name of the published version (defaults to a funny random name).
    :param model_name: Name of the parent model. May be left out if the project uses only one model.
    :param uses_dataset: Set to False to prevent the model version from linking to a dataset (default: True).
    :param dataset_name: Name of a dataset to be linked to the model version.
           May be left out if only one dataset was included in the training container
           or if *uses_dataset* was set to False.
    :param uses_pretrained: Set to True in order to link the model version to a pre-trained asset.
    :param pretrained_with: Reference to the pre-trained model asset to be linked (syntax: <model_name>:<version_name>).
           May be left out if only one pre-trained asset was included in the training container
           or if *uses_pretrained* wasn't set to True.

    :returns: A :ref:`ModelVersion <model-version-doc>` instance.
    
    :raise ResolutionError:
        - If the project uses zero or multiple models and none was specified as parent model.
        - If the specified parent model or pre-trained model is not present, or the given reference matched zero or multiple models.
        - If the specified dataset is not present, or the given reference matched zero ore multiple datasets.
    
    :Example:
    
    .. parsed-literal::
    
        publisher = Publisher()
        
        pickle.dump(my_classifier, open('/tmp/clf.pkl', 'wb'))
        
        publisher(
            details={
                'metrics': {'accuracy': 0.7, 'loss': 0.01},
                'params': {'gamma': 0.1, 'n_folds': 3}
            }
        )  # will look for model files in /tmp and associate the model version to a dataset, if available
    """
    
    def __init__(self):
        
        self.proj = Project.load()
        self.train = Training.load(ignore=True)
        self.mv_api = ModelVersionAPI(self.proj)
    
    def _infer_parent_model(self, model_name: str = None):
        
        if model_name is None:
            n_models = len(self.proj.models)
            
            if n_models == 1:
                model_name = self.proj.models[0].name
                err = None
            elif n_models == 0:
                err = "Project '{proj}' does not include any models."
            else:
                err = "Project '{proj}' includes {n_models} models."
            
            if err is not None:
                raise ResolutionError(
                    err.format(proj=self.proj.name, n_models=n_models)
                    + " Please specify which model you are publishing"
                )
        
        assert isinstance(model_name, str) and len(model_name) > 0
        return model_name
    
    def _infer_dataset(self, model_name: str, uses_dataset: bool = True, dataset_name: str = None):
        
        if uses_dataset:
            return dataset_meta(model=model_name, dataset=dataset_name)
        else:
            return None
    
    def _infer_pretrained(self, uses_pretrained: bool = False, pretrained_with: str = None):
        
        if uses_pretrained:
            model_name, version_name = (pretrained_with or ':').split(':')
            mv = movers_meta(model=model_name or None, version=version_name or None)
            return '{}:{}'.format(mv.model.name, mv.name)
        else:
            return None
    
    def __call__(self, src_path: str = Paths.TMP, details: dict = None,
                 version_name: str = None, model_name: str = None,
                 uses_dataset: bool = True, dataset_name: str = None,
                 uses_pretrained: bool = False, pretrained_with: str = None,
                 lightweight: bool = False):

        version_name = version_name or self.train.name
        model_name = self._infer_parent_model(model_name)
        ds = self._infer_dataset(model_name, uses_dataset, dataset_name)
        mv = None
        err = None

        try:
            mv = self.mv_api.new(
                name=version_name,
                model=model_name,
                ds=ds.name if ds else None,
                train=self.train.name,
                path=src_path,
                details=details or {},
                pretrained=self._infer_pretrained(uses_pretrained, pretrained_with),
                lightweight=lightweight,
                _replace=True
            )
        except Exception as e:
            LOG.warn("Model version {}:{} publish failed".format(model_name, version_name))
            err = e

        if self.train.name:
            self.train.update(mover=mv, ds=ds)

        if err:
            raise err

        if get_purpose() == DockerConst.Section.IDE:
            LOG.info("For testing purposes, model files will be moved to the deployed model path")
            MetaCargo(docs=[mv], section=DockerConst.Section.IDE).deploy()
            MoversCargo(mv, local=True, section=DockerConst.Section.IDE).move(src_path)
        
        return mv
