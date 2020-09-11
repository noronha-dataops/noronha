# -*- coding: utf-8 -*-

from cassandra import InvalidRequest

from noronha.api.ds import DatasetAPI
from noronha.api.main import NoronhaAPI
from noronha.api.movers import ModelVersionAPI
from noronha.bay.utils import FileSpec, StoreHierarchy
from noronha.bay.warehouse import get_lw_warehouse
from noronha.common.annotations import validate
from noronha.common.constants import WarehouseConst
from noronha.common.logging import LOG
from noronha.db.model import Model


class ModelAPI(NoronhaAPI):
    
    doc = Model
    valid = NoronhaAPI.valid
    
    def info(self, name):
        
        return super().info(name=name)
    
    def rm(self, name):
        
        LOG.warn("All datasets and model versions for the model '{}' will be deleted".format(name))
        self._decide("Would you like to proceed?", interrupt=True, default=True)
        report = {'Removed Datasets': [], 'Removed ModelVersions': []}
        
        for key, api in zip(report.keys(), [DatasetAPI(), ModelVersionAPI()]):
            for obj in api.lyst(model=name):
                api.rm(model=name, name=obj.name)
                report[key].append(obj.name)
        
        report.update(super().rm(name=name))

        try:
            get_lw_warehouse(section=WarehouseConst.Section.MODELS).drop_table(hierarchy=StoreHierarchy(name, 'dummy'))
        except (AssertionError, InvalidRequest):
            return report
        except Exception as e:
            LOG.debug("Did not update Cassandra. Error: {}".format(repr(e)))

        return report
    
    def lyst(self, _filter: dict = None, **kwargs):
        
        return super().lyst(_filter=_filter, **kwargs)
    
    @validate(name=valid.dns_safe, model_files=valid.list_of_dicts_or_none, data_files=valid.list_of_dicts_or_none)
    def new(self, **kwargs):
        
        if not kwargs.get('model_files'):
            LOG.warn("Creating model without a strict model persistence definition")
        
        if not kwargs.get('data_files'):
            LOG.warn("Creating model without a strict dataset files definition")
        
        return super().new(**kwargs)
    
    @validate(model_files=valid.list_of_dicts_or_none, data_files=valid.list_of_dicts_or_none)
    def update(self, name, **kwargs):
        
        if kwargs.get('model_files'):
            LOG.warn("If 'model_files' definition is changed, old model versions may become unusable")
            self._decide("Do you want to proceed?", default=True, interrupt=True)
        
        if kwargs.get('data_files'):
            LOG.warn("If 'data_files' definition is changed, old datasets may become unusable")
            self._decide("Do you want to proceed?", default=True, interrupt=True)

        current: Model = self.doc.find_one(name=name)
        
        updated: Model = super().update(
            filter_kwargs=dict(name=name),
            update_kwargs=kwargs
        )

        if kwargs.get('model_files'):

            try:
                get_lw_warehouse(section=WarehouseConst.Section.MODELS).update_schema(
                    hierarchy=StoreHierarchy(updated.name, 'dummy'),
                    new_schema=[FileSpec.from_doc(d) for d in updated.model_files],
                    old_schema=[FileSpec.from_doc(d) for d in current.model_files])
            except (AssertionError, InvalidRequest):
                return updated
            except Exception as e:
                LOG.debug("Did not update Cassandra. Error: {}".format(repr(e)))

        return updated
