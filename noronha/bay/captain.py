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

"""Module used to orchestrate container deployment"""

import logging
import os
import time
from abc import ABC, abstractmethod
from conu import DockerBackend, K8sBackend
from conu.backend.docker.container import DockerContainer
from conu.backend.k8s.deployment import Deployment
from conu.backend.k8s.pod import Pod
from conu.backend.k8s.pod import PodPhase
from conu.exceptions import ConuException
from datetime import datetime
from docker.errors import APIError as DockerAPIError
from docker.types import ServiceMode, TaskTemplate, ContainerSpec, Resources, Healthcheck
from kaptan import Kaptan
from kubernetes import utils as k8s_utils
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException as K8sApiException
from kubernetes.stream import stream
import random_name
from subprocess import Popen, PIPE
from typing import Type, List

from noronha.bay.cargo import Cargo, EmptyCargo, MappedCargo, HeavyCargo, SharedCargo
from noronha.bay.compass import DockerCompass, CaptainCompass, SwarmCompass, KubeCompass
from noronha.bay.shipyard import ImageSpec
from noronha.bay.utils import Workpath
from noronha.common.annotations import Configured, Patient, patient
from noronha.common.conf import CaptainConf
from noronha.common.constants import DockerConst, Encoding, DateFmt, Regex, LoggerConst
from noronha.common.errors import ResolutionError, NhaDockerError, PatientError, ConfigurationError
from noronha.common.logging import Logged
from noronha.common.parser import dict_to_kv_list, assert_str, StructCleaner, join_dicts


class Captain(ABC, Configured, Patient, Logged):
    
    conf = CaptainConf
    compass_cls: Type[CaptainCompass] = None
    
    def __init__(self, section: str, resource_profile: str = None, **kwargs):
        
        Logged.__init__(self, log=kwargs.get('log'))
        self.docker_compass = DockerCompass()
        self.compass = self.compass_cls()
        self.section = section
        self.interrupted = False
        self.cleaner = StructCleaner()
        self.healthcheck = self.compass.healthcheck
        self.resources = self.compass.get_resource_profile(resource_profile or section)
        Patient.__init__(self, timeout=self.compass.api_timeout)
    
    @abstractmethod
    def run(self, img: ImageSpec, env_vars, mounts: List[str], cargos: List[Cargo], ports, cmd: list, name: str,
            foreground=False):
        
        pass
    
    @abstractmethod
    def deploy(self, img: ImageSpec, env_vars, mounts: List[str], cargos: List[Cargo], ports, cmd: list, name: str,
               tasks: int = 1, allow_probe=False):
        
        pass
    
    @abstractmethod
    def dispose_run(self, alias: str):
        
        pass
    
    @abstractmethod
    def dispose_deploy(self, alias: str):
        
        pass
    
    @abstractmethod
    def rm_vol(self, cargo: Cargo, ignore=False):
        
        pass
    
    def close(self):
        
        pass
    
    def mule_name(self, mule_alias: str = None):
        
        return '{}-mule'.format(
            mule_alias or random_name.generate_name()
        )
    
    def _find_sth(self, what, method, name, key=None, **kwargs):
        
        items = list(filter(
            key or (lambda i: i.name.lstrip('/') == name),
            method(**kwargs)
        ))
        
        if len(items) == 0:
            return None
        elif len(items) == 1:
            return items[0]
        else:
            raise NotImplementedError("Multiple {} with name '{}'".format(what, name))

    def get_node_port(self, svc_name: str):

        pass
    
    @abstractmethod
    def list_cont_or_pod_ids(self):
        
        pass


class SwarmCaptain(Captain):
    
    compass_cls = SwarmCompass
    
    _CPU_RATE = 10**9  # vCores to nanoCores
    _MEM_RATE = 1024*1024  # MB to bytes
    _SEC_RATE = 10**9  # seconds to nanoseconds
    
    def __init__(self, section: str, **kwargs):
        
        super().__init__(section, **kwargs)
        
        if self.LOG.name != LoggerConst.DEFAULT_NAME:
            self.LOG.warn(
                "Using Docker Swarm as container manager."
                "This is not recommended for distributed environments"
            )
        
        self.docker_api = self.docker_compass.get_api()
        self.docker_backend = DockerBackend(logging_level=logging.ERROR)
    
    def run(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, name: str, foreground=False):
        
        self.make_name_available(name)
        [self.load_vol(v, name) for v in cargos]
        image = self.docker_backend.ImageClass(img.repo, tag=img.tag)
        
        additional_opts = \
            self.conu_ports(ports) + \
            self.conu_env_vars(env_vars) + \
            self.conu_name(name) + \
            self.conu_resources()
        
        kwargs = self.cleaner(dict(
            command=cmd,
            volumes=self.conu_mounts(mounts) + self.conu_vols(cargos),
            additional_opts=additional_opts,
            popen_params=dict(
                stdout=self.LOG.file_handle,
                stderr=self.LOG.file_handle
            ) if self.LOG.background else None
        ))
        
        if foreground:
            cont = image.run_via_binary_in_foreground(**kwargs)
            self.watch_cont(cont)
        else:
            cont = image.run_via_binary(**kwargs)
        
        return cont
    
    def deploy(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, name: str, tasks: int = 1,
               allow_probe=False):
        
        [self.load_vol(v, name) for v in cargos]
        self.assert_network()
        depl = self.find_depl(name)
        
        kwargs = self.cleaner(dict(
            name=name,
            endpoint_spec=dict(Ports=self.swarm_ports(ports)),
            networks=[DockerConst.NETWORK],
            mode=ServiceMode('replicated', replicas=tasks),
            task_template=TaskTemplate(
                force_update=5,
                resources=self.swarm_resources(),
                container_spec=ContainerSpec(
                    command=cmd,
                    image=img.target,
                    env=env_vars,
                    mounts=mounts + [v.mount for v in cargos],
                    healthcheck=self.swarm_healthcheck(allow_probe)
                )
            )
        ))
        
        if depl is None:
            self.LOG.debug("Creating container service '{}' with kwargs:".format(name))
            self.LOG.debug(kwargs)
            return self.docker_api.create_service(**kwargs)
        else:
            kwargs.update(service=depl['ID'], version=depl['Version']['Index'])
            self.LOG.debug("Updating container service '{}' with kwargs:".format(name))
            self.LOG.debug(kwargs)
            return self.docker_api.update_service(**kwargs)
    
    def dispose_run(self, name: str):
        
        cont = self.find_cont(name)
        
        if cont is not None:
            return self.rm_cont(cont)
        else:
            return False
    
    def dispose_deploy(self, name: str):
        
        return self.rm_depl(name)
    
    @patient
    def rm_vol(self, cargo: Cargo, ignore=False):
        
        if isinstance(cargo, MappedCargo):
            return False
        
        try:
            self.docker_api.remove_volume(name=cargo.name, force=True)
            return True
        except DockerAPIError as e:
            if ignore:
                self.LOG.error(e)
                return False
            else:
                msg = "Waiting up to {} seconds for removal of volume {}".format(self.timeout, cargo.name)
                raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
    
    def rm_cont(self, x: DockerContainer):
        
        try:
            x.delete(force=True)
        except DockerAPIError as e:
            self.LOG.error(e)
            return False
        else:
            return True
    
    def rm_depl(self, name: str):
        
        try:
            self.docker_api.remove_service(name)
        except Exception as e:
            self.LOG.error(e)
            return False
        else:
            return True
    
    def list_cont_or_pod_ids(self):
        
        return [
            cont.get_id() for cont in
            self.docker_backend.list_containers()
        ]
    
    def find_cont(self, name):
        
        return self._find_sth(
            what='containers',
            method=self.docker_backend.list_containers,
            name=name
        )
    
    def find_depl(self, name):
        
        return self._find_sth(
            what='deployments',
            method=self.docker_api.services,
            filters=dict(name=name),
            key=lambda _: True,
            name=name
        )
    
    def find_net(self):
        
        return self._find_sth(
            what='networks',
            method=self.docker_api.networks,
            names=[DockerConst.NETWORK],
            key=lambda _: True,
            name=DockerConst.NETWORK
        )
    
    def make_name_available(self, name):
        
        existing = self.find_cont(name)
        
        if existing is not None:
            self.LOG.warn("Removing old container '{}'".format(name))
            self.rm_cont(existing)
    
    def watch_cont(self, container: DockerContainer):
        
        try:
            while container.is_running():
                time.sleep(1)
        except (KeyboardInterrupt, InterruptedError):
            self.interrupted = True
    
    def wait_for_net(self):
        
        for _ in range(self.timeout):
            if self.find_net() is None:
                time.sleep(1)
            else:
                break
        else:
            raise NhaDockerError("Timed out waiting for Docker network")
    
    def assert_network(self):
        
        if self.find_net() is not None:
            return
        
        kwargs = dict(
            name=DockerConst.NETWORK,
            driver="overlay",
            attachable=False,
            scope="global",
            ingress=False
        )  # standard properties for a network that is meant to be used only by Swarm services
        
        self.LOG.info("Creating Docker network")
        self.LOG.debug(kwargs)
        self.docker_api.create_network(**kwargs)
        self.wait_for_net()
    
    def assert_vol(self, cargo: Cargo):
        
        vols = self.docker_api.volumes(dict(name=cargo.name))
        
        if len(vols) == 0:
            self.docker_api.create_volume(name=cargo.name)
            
            return True
        elif len(vols) == 1:
            return False
        else:
            return NotImplementedError()
    
    def load_vol(self, cargo: Cargo, mule_alias: str = None):
        
        work_path, mule, error = None, None, None
        
        if not isinstance(cargo, MappedCargo):
            self.assert_vol(cargo)
        
        if isinstance(cargo, EmptyCargo) or len(cargo.contents) == 0:
            return False
        
        try:
            self.LOG.debug("Loading volume '{}'".format(cargo.name))
            mule = self.get_mule(cargo, mule_alias)
            self.clear_mule(mule)
            work_path = Workpath.get_tmp()
            kwargs = dict(include_heavy_cargos=True) if isinstance(cargo, SharedCargo) else {}
            cargo.deploy(work_path, **kwargs)
            
            for file_name in os.listdir(work_path):
                self.copy_to(src=work_path.join(file_name), dest=DockerConst.STG_MOUNT, cont=mule)
        
        except Exception as e:
            error = e
        else:
            return True
        finally:
            if work_path is not None:
                work_path.dispose()
            if mule is not None:
                self.rm_cont(mule)
            if error is not None:
                self.rm_vol(cargo, ignore=True)
                raise error
    
    def get_mule(self, cargo: Cargo, mule_alias: str = None):
        
        repo, tag = DockerConst.MULE_IMG.split(':')
        image = self.docker_backend.ImageClass(repo, tag=tag)
        name = self.mule_name(mule_alias)
        
        kwargs = dict(
            additional_opts=self.conu_name(name),
            command=DockerConst.MULE_CMD,
            volumes=[(cargo.name, DockerConst.STG_MOUNT, 'rw')]
        )
        
        return image.run_via_binary(**kwargs)
    
    def clear_mule(self, mule: DockerContainer):
        
        ls_output = mule.execute('ls {}'.format(DockerConst.STG_MOUNT))
        
        if not ls_output:
            return
        
        for file_name in ls_output[0].strip().decode('utf-8').split('\n'):
            mule.execute('rm -rf {}/{}'.format(DockerConst.STG_MOUNT, file_name))
    
    def copy_to(self, src: str, dest: str, cont: DockerContainer):
        
        cont.copy_to(src=src, dest=dest)
    
    def _exec_in_cont(self, cont: DockerContainer, cmd: str):
        
        cont.execute(cmd.split(' '), blocking=True)
    
    def conu_vols(self, vols: List[Cargo]):
        
        return [tuple(v.mount.split(':')) for v in vols]
    
    def conu_mounts(self, mounts: List[str]):
        
        return [tuple(m.split(':')) for m in mounts]
    
    def conu_ports(self, ports: list):
        
        ports_opt = []
        
        for p in ports:
            ports_opt += ['-p', p]
        
        return ports_opt
    
    def conu_env_vars(self, env_vars: dict):
        
        env_vars_opt = []
        
        for e in dict_to_kv_list(env_vars):
            env_vars_opt += ['-e', e]
        
        return env_vars_opt
    
    def conu_name(self, name: str = None):
        
        if name is None:
            return []
        else:
            return ['--name', name]
    
    def swarm_ports(self, ports):
        
        port_specs = []
        
        for p in ports:
            if ':' in p:
                p_from, p_to = p.split(':')
                port_specs.append(dict(
                    PublishedPort=int(p_from),
                    TargetPort=int(p_to),
                    Protocol='tcp'
                ))
            else:
                continue  # single port exposure is not necessary in swarm mode
        
        return port_specs
    
    def swarm_resources(self):
        
        if self.resources is None:
            return None
        else:
            if self.resources.get('enable_gpu', False):
                return Resources(
                    cpu_limit=int(self.resources['limits']['cpu'] * self._CPU_RATE),
                    mem_limit=self.resources['limits']['memory'] * self._MEM_RATE,
                    cpu_reservation=int(self.resources['requests']['cpu'] * self._CPU_RATE),
                    mem_reservation=self.resources['requests']['memory'] * self._MEM_RATE,
                    generic_resources={'gpu': 1}
                )
            else:
                return Resources(
                    cpu_limit=int(self.resources['limits']['cpu'] * self._CPU_RATE),
                    mem_limit=self.resources['limits']['memory'] * self._MEM_RATE,
                    cpu_reservation=int(self.resources['requests']['cpu'] * self._CPU_RATE),
                    mem_reservation=self.resources['requests']['memory'] * self._MEM_RATE
                )
    
    def conu_resources(self):
        
        if self.resources is None:
            return []
        else:
            res = [
                '--cpus', str(self.resources['limits']['cpu']),
                '--memory-reservation', '{}m'.format(self.resources['requests']['memory'])
            ]

            if self.resources.get('enable_gpu', False):
                res = res + ['--gpus', 'all']

            return res
    
    def swarm_healthcheck(self, allow_probe=False):
        
        if allow_probe and self.healthcheck['enabled']:
            return Healthcheck(
                test=["CMD", "curl", "-f", "http://localhost:8080/health"],
                interval=self.healthcheck['interval']*self._SEC_RATE,
                timeout=self.healthcheck['timeout']*self._SEC_RATE,
                retries=self.healthcheck['retries'],
                start_period=self.healthcheck['start_period']*self._SEC_RATE
            )
        else:
            return None


class KubeCaptain(Captain):
    
    compass_cls = KubeCompass
    
    def __init__(self, section: str, **kwargs):
        
        super().__init__(section, **kwargs)
        self.secret = self.docker_compass.secret
        self.namespace = self.compass.get_namespace()
        self.nfs = self.compass.get_nfs_server()
        self.stg_cls = self.compass.get_stg_cls(section)
        self.mule = None
        self.assert_namespace()
        k8s_config.load_kube_config()
        self.api_client = k8s_client.ApiClient()
    
    def run(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, name: str, foreground=False):
        
        [self.load_vol(v, name) for v in cargos]
        self.make_name_available(name)
        vol_refs, vol_defs = self.kube_vols(cargos)
        mount_refs, mount_defs = self.kube_mounts(mounts)
        port_refs, port_defs = self.kube_svc_ports(name, ports)
        
        container = dict(
            name=name,
            image=img.target,
            imagePullPolicy='Always',
            command=cmd,
            resources=self.kube_resources(),
            volumeMounts=vol_refs + mount_refs,
            env=self.kube_env_vars(env_vars),
            ports=port_refs,
        )
        
        template = self.cleaner(dict(
            apiVersion="v1",
            kind="Pod",
            metadata=dict(name=name, labels={'app': name}),
            spec={
                'containers': [container],
                'volumes': vol_defs + mount_defs,
                'imagePullSecrets': [{'name': self.secret}]
            }
        ))
        
        self.LOG.info("Creating Pod '{}'".format(name))
        self.LOG.debug(template)
        
        pod = Pod(namespace=self.namespace, from_template=template)
        self.handle_svc(name, port_defs)
        self.wait_for_pod(pod)
        
        if foreground:
            self.watch_pod(pod)
        
        return pod
    
    def deploy(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, name: str, tasks: int = 1,
               allow_probe=False, delay_readiness: int = 0):
        
        [self.load_vol(v, name) for v in cargos]
        vol_refs, vol_defs = self.kube_vols(cargos)
        mount_refs, mount_defs = self.kube_mounts(mounts)
        port_refs, port_defs = self.kube_svc_ports(name, ports)
        
        container = dict(
            name=name,
            image=img.target,
            imagePullPolicy='Always',
            command=cmd,
            resources=self.kube_resources(),
            volumeMounts=vol_refs + mount_refs,
            env=self.kube_env_vars(env_vars),
            ports=port_refs,
            livenessProbe=self.kube_healthcheck(allow_probe),
            readinessProbe=self.kube_readiness(delay_readiness)
        )
        
        template = self.cleaner(dict(
            apiVersion="apps/v1",
            kind="Deployment",
            metadata={'name': name},
            spec=dict(
                replicas=tasks,
                selector={'matchLabels': {'app': name}},
                template=dict(
                    metadata={
                        'labels': {'app': name},
                        'annotations': {'updated': datetime.now().strftime(DateFmt.READABLE)}
                    },
                    spec={
                        'containers': [container],
                        'volumes': vol_defs + mount_defs,
                        'imagePullSecrets': [{'name': self.secret}]
                    }
                )
            )
        ))

        if self.find_depl(name) is None:
            self.LOG.info("Creating deployment '{}'".format(name))
            self.LOG.debug(template)
            yaml = Kaptan().import_config(template).export(handler='yaml')
            depl = Deployment(namespace=self.namespace, create_in_cluster=True, from_template=yaml)
        else:
            self.LOG.info("Updating deployment '{}'".format(name))
            self.LOG.debug(template)
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                k8s_backend.apps_api.replace_namespaced_deployment(name, self.namespace, template)
            depl = self.find_depl(name)
        
        self.handle_svc(name, port_defs)
        self.handle_autoscaler(name)

        return depl

    def dispose_run(self, name: str):
        
        self.rm_pod(name)
        self.rm_svc(name)
    
    def dispose_deploy(self, name: str):
        
        self.rm_depl(name)
        self.rm_svc(name)
    
    def rm_vol(self, cargo: Cargo, ignore=False):
        
        if isinstance(cargo, MappedCargo):
            return False
        elif isinstance(cargo, EmptyCargo):  # PVC
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                k8s_backend.core_api.delete_namespaced_persistent_volume_claim(cargo.name, self.namespace)
            return True
        
        if self.mule is None:
            if ignore:
                self.LOG.warn("Missing auxiliary Pod for deletion of volume '{}'".format(cargo.name))
                return False
            else:
                self.prepare_mule(cargo.name)
        
        try:
            vol_path = os.path.join(DockerConst.STG_MOUNT, cargo.name)
            self._exec_in_pod(self.mule, 'rm -rf {}'.format(vol_path))
            return True
        except Exception as e:
            if ignore:
                self.LOG.debug(repr(e))
                return False
            else:
                raise e

    @patient
    def rm_pod(self, name: str, ignore=True):
        
        try:
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                k8s_backend.core_api.delete_namespaced_pod(
                    name=name, namespace=self.namespace, grace_period_seconds=0)
        except (ConuException, K8sApiException) as e:
            msg = "Waiting up to {} seconds to kill Pod '{}'".format(self.timeout, name)
            raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
        except Exception as e:
            self.LOG.info("Could not patiently delete Pod: {}".format(name))
            if ignore:
                self.LOG.debug(repr(e))
            else:
                raise e

    @patient
    def rm_depl(self, name: str, ignore=True):
        
        try:
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                k8s_backend.apps_api.delete_namespaced_deployment(
                    name=name, namespace=self.namespace, grace_period_seconds=0)
        except (ConuException, K8sApiException) as e:
            msg = "Waiting up to {} seconds to kill Deployment '{}'".format(self.timeout, name)
            raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
        except Exception as e:
            self.LOG.info("Could not patiently delete Deployment: {}".format(name))
            if ignore:
                self.LOG.debug(repr(e))
            else:
                raise e
    
    def rm_svc(self, name: str, ignore=True):
        
        try:
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                k8s_backend.core_api.delete_namespaced_service(
                    name=name, namespace=self.namespace, grace_period_seconds=0)
        except Exception as e:
            self.LOG.debug("Could not delete service: {}".format(name))
            if ignore:
                self.LOG.debug(repr(e))
            else:
                raise e
    
    def close(self):
        
        if self.mule is not None:
            self.rm_pod(self.mule.name)
    
    def list_cont_or_pod_ids(self):

        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            lyst = [pod.metadata.name for pod in
                    k8s_backend.core_api.list_namespaced_pod(namespace=self.namespace).items]
        
        return lyst
    
    @patient
    def _find_sth(self, what, name, method, **kwargs):
        
        try:
            return super()._find_sth(
                what=what,
                name=name,
                method=lambda: method(self.namespace).items,
                key=lambda i: i.metadata.name == name
            )
        except (ConuException, K8sApiException) as e:
            msg = "Waiting up to {} seconds to find {} '{}'".format(self.timeout, what, name)
            raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
    
    def find_vol(self, cargo: Cargo):

        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            result = self._find_sth(
                what='persistent volume claims',
                method=k8s_backend.core_api.list_namespaced_persistent_volume_claim,
                name=cargo.name
            )
        
        return result
    
    @patient
    def find_pod(self, name):
        
        try:
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                result = super()._find_sth(
                    what='pods',
                    method=k8s_backend.list_pods,
                    name=name,
                    namespace=self.namespace
                )

            return result
        except (ConuException, K8sApiException) as e:
            msg = "Waiting up to {} seconds to find {} '{}'".format(self.timeout, 'pod', name)
            raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
    
    def find_depl(self, name):

        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            result = self._find_sth(
                what='deployments',
                method=k8s_backend.apps_api.list_namespaced_deployment,
                name=name
            )
        
        return result
    
    def find_svc(self, name):

        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            result = self._find_sth(
                what='services',
                method=k8s_backend.core_api.list_namespaced_service,
                name=name
            )
        
        return result

    def find_autoscaler(self, name: str):

        api_response = k8s_client.AutoscalingV1Api(self.api_client). \
            list_namespaced_horizontal_pod_autoscaler(namespace=self.namespace).to_dict()

        for i in api_response.get('items', []):
            if i.get('metadata', {}).get('name', '') == name:
                return i

        return None

    def handle_autoscaler(self, name: str):

        if self.resources and self.resources.get('auto_scale', False):

            if self.find_autoscaler(name):
                self.LOG.debug('Removing old autoscaler: {}'.format(name))
                k8s_client.AutoscalingV1Api(self.api_client). \
                    delete_namespaced_horizontal_pod_autoscaler(name=name, namespace=self.namespace)

            self.LOG.info("Creating horizontal Pod autoscaler")

            template = dict(
                apiVersion='autoscaling/v1',
                kind='HorizontalPodAutoscaler',
                metadata=dict(
                    name=name,
                    namespace=self.namespace),
                spec=dict(
                    minReplicas=self.resources.get('minReplicas', 1),
                    maxReplicas=self.resources.get('maxReplicas', 10),
                    targetCPUUtilizationPercentage=self.resources.get('targetCPUUtilizationPercentage', 50),
                    scaleTargetRef=dict(
                        apiVersion='apps/v1',
                        name=name,
                        kind='Deployment')
                )
            )

            try:
                k8s_utils.create_from_dict(self.api_client, template)
                self.LOG.debug(template)
            except Exception as e:
                self.LOG.debug("Failed to create autoscaler: {}".format(name))
                self.LOG.debug(repr(e))
    
    def make_name_available(self, name):
        
        existing = self.find_pod(name)
        
        if existing is not None:
            self.LOG.warn("Removing old pod '{}'".format(name))
            self.rm_pod(existing.name)
    
    def watch_pod(self, pod: Pod):

        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            logs = k8s_backend.core_api.read_namespaced_pod_log(
                name=pod.name,
                namespace=self.namespace,
                follow=True,
                _preload_content=False
            )
        
        try:
            for line in logs:
                self.LOG.echo(line.decode(Encoding.UTF_8).strip())
        except (KeyboardInterrupt, InterruptedError):
            self.interrupted = True
    
    @patient
    def wait_for_pod(self, pod: Pod):
        
        try:
            if pod.get_phase() == PodPhase.RUNNING and pod.is_ready():
                return
            else:
                raise NhaDockerError("Timed out waiting for pod '{}'".format(pod.name))
        except (ConuException, K8sApiException, NhaDockerError) as e:
            msg = "Waiting up to {} seconds for pod '{}' to start".format(self.timeout, pod.name)
            raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
    
    @patient
    def assert_namespace(self):
        
        try:
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                assert super()._find_sth(
                    what='namespaces',
                    name=self.namespace,
                    method=lambda: k8s_backend.core_api.list_namespace().items,
                    key=lambda i: i.metadata.name == self.namespace
                ) is not None, ConfigurationError("Namespace '{}' does not exist".format(self.namespace))
        except (ConuException, K8sApiException) as e:
            msg = "Waiting up to {} seconds to find {} '{}'".format(self.timeout, 'namespace', self.namespace)
            raise PatientError(wait_callback=lambda: self.LOG.info(msg), original_exception=e)
    
    def assert_vol(self, cargo: Cargo):
        
        storage = '{}Gi'.format(max(int(cargo.require_mb/1024), 1))
        
        template = dict(
            apiVersion="v1",
            kind="PersistentVolumeClaim",
            metadata={'name': cargo.name},
            spec=dict(
                storageClassName=self.stg_cls,
                accessModes=['ReadWriteOnce'],
                resources={'requests': {'storage': storage}}
            )
        )
        
        if self.find_vol(cargo) is None:
            self.LOG.info("Creating persistent volume claim '{}'".format(cargo.name))
            self.LOG.debug(template)
            with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
                k8s_backend.core_api.create_namespaced_persistent_volume_claim(self.namespace, template)
            return True
        else:
            return False
    
    def handle_svc(self, name, port_defs):
        
        if self.find_svc(name) is not None:
            self.LOG.info("Removing old version of service '{}'".format(name))
            self.rm_svc(name)
        
        if len(port_defs) == 0:
            self.LOG.info('Skipping service creation')
            return
        
        svc = dict(
            apiVersion='v1',
            kind='Service',
            metadata={'name': name},
            spec=dict(
                selector={'app': name},
                type='LoadBalancer' if self.compass.get_use_lb() else 'NodePort',
                ports=port_defs
            )
        )
        
        self.LOG.info("Creating service '{}'".format(name))
        self.LOG.debug(svc)
        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            k8s_backend.core_api.create_namespaced_service(self.namespace, svc)
    
    def load_vol(self, cargo: Cargo, mule_alias: str = None):
        
        if isinstance(cargo, EmptyCargo):
            self.assert_vol(cargo)
            return
        elif isinstance(cargo, MappedCargo):
            return
        
        work_path, error = None, None
        vol_path = os.path.join(DockerConst.STG_MOUNT, cargo.name)
        
        try:
            self.prepare_mule(mule_alias)
            self.LOG.debug("Creating volume '{}'".format(cargo.name))
            self.clear_mule(self.mule, vol_path)
            work_path = Workpath.get_tmp()
            
            if not isinstance(cargo, HeavyCargo):
                cargo.deploy(work_path)
                
                for file_name in os.listdir(work_path):
                    self.copy_to(src=work_path.join(file_name), dest=vol_path, pod=self.mule)
            
            if isinstance(cargo, (HeavyCargo, SharedCargo)):
                for msg, cmd in cargo.get_deployables(vol_path):
                    self.LOG.info(msg)
                    self._exec_in_pod(self.mule, cmd)
        
        except Exception as e:
            self.rm_vol(cargo, ignore=True)
            raise e
        finally:
            if work_path is not None:
                work_path.dispose()
    
    def prepare_mule(self, mule_alias: str = None):
        
        if self.mule is not None:
            return self.mule
        
        name = self.mule_name(mule_alias)
        self.make_name_available(name)
        vol_refs, vol_defs = self.mule_mount(name)
        
        container = dict(
            name=name,
            image=DockerConst.MULE_IMG,
            command=DockerConst.MULE_CMD,
            volumeMounts=vol_refs
        )
        
        template = dict(
            apiVersion="v1",
            kind="Pod",
            metadata=dict(name=name, labels={'app': name}),
            spec={
                'containers': [container],
                'volumes': vol_defs
            }
        )
        
        self.LOG.debug("Creating auxiliar Pod '{}' for handling volumes".format(name))
        self.LOG.debug(template)
        
        self.mule = Pod(namespace=self.namespace, from_template=template)
        self.wait_for_pod(self.mule)
    
    def clear_mule(self, mule: Pod, vol_path: str):
        
        self._exec_in_pod(mule, 'mkdir -p {}'.format(vol_path))
        ls_output = self._exec_in_pod(mule, 'ls {}'.format(vol_path)).strip()
        
        if not ls_output:
            return
        
        for name in ls_output.split('\n'):
            self._exec_in_pod(mule, 'rm -rf {}/{}'.format(vol_path, name))
    
    def copy_to(self, src: str, dest: str, pod: Pod):
        
        out, err = Popen(
            'kubectl cp --namespace={namespace} {src} {pod}:{dest}'.format(
                src=src,
                dest=dest,
                pod=pod.name,
                namespace=self.namespace
            ).split(' '),
            stdout=PIPE, stderr=PIPE
        ).communicate()
        
        if err:
            raise RuntimeError(assert_str(err).strip())
        else:
            return assert_str(out).strip()
    
    def _exec_in_pod(self, pod: Pod, cmd, stderr=True, stdin=False, stdout=True, tty=False):

        with K8sBackend(logging_level=logging.ERROR) as k8s_backend:
            result = '\n'.join([
                stream(
                    k8s_backend.core_api.connect_get_namespaced_pod_exec,
                    name=pod.name, namespace=self.namespace, command=c.strip().split(' '),
                    stderr=stderr, stdin=stdin, stdout=stdout, tty=tty
                )
                for c in Regex.CMD_DELIMITER.split(cmd)
            ])
        
        return result
    
    def mule_mount(self, mule_name):
        
        cargo = MappedCargo(
            name=mule_name,
            mount_to=DockerConst.STG_MOUNT,
            src=self.nfs['path'],
            nfs=True
        )
        
        return self.kube_vols([cargo])
    
    def kube_mounts(self, mounts: List[str]):
        
        mounts = [
            dict(src=mount_tuple[0], dest=mount_tuple[1]) for mount_tuple in
            [mount.split(':') for mount in mounts]
        ]
        
        cargo = [
            MappedCargo(
                name='extra-mount-{}'.format(index),
                mount_to=mount['dest'],
                src=mount['src']
            )
            for index, mount in enumerate(mounts)
        ]
        
        return self.kube_vols(cargo)
    
    def kube_vols(self, cargos: List[Cargo] = None):
        
        refs, defs = [], []
        
        for cargo in cargos:
            name = cargo.name
            
            if isinstance(cargo, EmptyCargo):
                kwargs = dict(persistentVolumeClaim={'claimName': cargo.name})
            elif isinstance(cargo, MappedCargo) and not cargo.nfs:
                kwargs = dict(hostPath={'path': cargo.src, 'type': cargo.tipe})
            else:
                if isinstance(cargo, MappedCargo) and cargo.nfs:  # mule mount to nfs root
                    nfs_path = cargo.src
                else:
                    nfs_path = os.path.join(self.nfs['path'], name)
                
                kwargs = dict(nfs={
                    'server': self.nfs['server'],
                    'path': nfs_path
                })
            
            refs.append(dict(
                name=cargo.name,
                mountPath=cargo.mount_to
            ))
            
            defs.append(dict(
                name=cargo.name,
                **kwargs
            ))
        
        return refs, defs
    
    def kube_svc_ports(self, name: str, ports: List[str]):
        
        refs, defs = [], []
        
        for port in ports:
            parts = port.split(':')
            
            if len(parts) == 1:
                src = None
                tgt = int(parts[0])
            elif len(parts) == 2:
                src = int(parts[0])
                tgt = int(parts[1])
            else:
                raise NotImplementedError()
            
            refs.append({'containerPort': tgt})
            defs.append(self.cleaner({
                'name': '{}-{}'.format(name, tgt),
                'port': tgt,
                'targetPort': tgt,
                'nodePort': src
            }))
        
        return refs, defs
    
    def kube_env_vars(self, env_vars: dict):
        
        return [
            dict(name=k, value=v)
            for k, v in env_vars.items()
        ]
    
    def kube_resources(self):
        
        if self.resources is None:
            return None
        
        res = {}
        
        for key in ['requests', 'limits']:
            res[key] = dict(
                cpu=self.resources[key]['cpu'],
                memory=self.kube_memory(self.resources[key]['memory'])
            )

        if self.resources.get('enable_gpu', False):
            res['limits'] = join_dicts(res['limits'], {"nvidia.com/gpu": 1})
        
        return res
    
    def kube_memory(self, mem):
        
        if mem >= 1024:
            mem = int(mem/1024)
            unit = 'Gi'
        else:
            unit = 'Mi'
        
        return '{}{}'.format(mem, unit)
    
    def kube_healthcheck(self, allow_probe=False):
        
        if allow_probe and self.healthcheck['enabled']:
            return dict(
                exec=dict(command=["curl", "-f", "http://localhost:8080/health"]),
                periodSeconds=self.healthcheck['interval'],
                timeoutSeconds=self.healthcheck['timeout'],
                failureThreshold=self.healthcheck['retries'],
                initialDelaySeconds=self.healthcheck['start_period']
            )
        else:
            return None

    def kube_readiness(self, delay_readiness=0):

        if isinstance(delay_readiness, int) and delay_readiness > 0:
            return dict(
                exec=dict(command=["curl", "-f", "http://localhost:8080/health"]),
                initialDelaySeconds=delay_readiness,
                periodSeconds=30,
                failureThreshold=5
            )
        else:
            return None

    def get_node_port(self, svc_name: str):

        svc = self.find_svc(svc_name)
        svc = svc.to_dict() if svc is not None else {}
        ports = svc.get('spec', {}).get('ports', [])
        return ports[0]['node_port'] if len(ports) == 1 else None


def get_captain(section: str = DockerConst.Section.IDE, **kwargs):
    
    manager_ref = CaptainCompass().tipe
    cls_lookup = {
        DockerConst.Managers.SWARM: SwarmCaptain,
        DockerConst.Managers.KUBE: KubeCaptain
    }
    
    try:
        capitain_cls: Type[SwarmCaptain, KubeCaptain] = cls_lookup[manager_ref.strip().lower()]
    except (KeyError, AttributeError):
        raise ResolutionError(
            "Could not resolve container manager by reference '{}'. Options are: {}"
            .format(manager_ref, list(cls_lookup.keys()))
        )
    else:
        return capitain_cls(section, **kwargs)
