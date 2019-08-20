# -*- coding: utf-8 -*-

import logging
import os
import time
from abc import ABC, abstractmethod
from conu import DockerBackend, K8sBackend
from conu.backend.docker.container import DockerContainer
from conu.backend.k8s.deployment import Deployment
from conu.backend.k8s.pod import Pod
from datetime import datetime
from docker.errors import APIError as DockerAPIError
from docker.types import ServiceMode, TaskTemplate, ContainerSpec
from kaptan import Kaptan
from kubernetes.stream import stream
import random_name
from typing import Type, List

from noronha.bay.cargo import Cargo, EmptyCargo, MappedCargo
from noronha.bay.compass import DockerCompass, CaptainCompass, SwarmCompass, KubeCompass
from noronha.bay.shipyard import ImageSpec
from noronha.bay.utils import Workpath
from noronha.common.annotations import Configured
from noronha.common.conf import CaptainConf
from noronha.common.constants import DockerConst, Encoding, DateFmt
from noronha.common.errors import ResolutionError, NhaDockerError
from noronha.common.logging import LOG
from noronha.common.utils import dict_to_kv_list, run_bash_cmd, StructCleaner


class Captain(ABC, Configured):
    
    conf = CaptainConf
    compass_cls: Type[CaptainCompass] = None
    
    def __init__(self, section: str):
        
        self.docker_compass = DockerCompass()
        self.captain_compass = self.compass_cls()
        self.section = section
        self.interrupted = False
    
    @abstractmethod
    def run(self, img: ImageSpec, env_vars, mounts: List[str], cargos: List[Cargo], ports, cmd: list, alias: str,
            foreground=False):
        
        pass
    
    @abstractmethod
    def deploy(self, img: ImageSpec, env_vars, mounts: List[str], cargos: List[Cargo], ports, cmd: list, alias: str,
               tasks: int = 1):
        
        pass
    
    @abstractmethod
    def dispose_run(self, alias: str, force=False):
        
        pass
    
    @abstractmethod
    def dispose_deploy(self, alias: str, force=False):
        
        pass
    
    @abstractmethod
    def rm_vol(self, cargo: Cargo, force=False):
        
        pass
    
    def close(self):
        
        pass
    
    def with_prefix(self, suffix: str):
        
        return '{}-{}'.format(self.section, suffix)
    
    def mule_name(self, mule_alias: str = None):
        
        return self.with_prefix(
            'mule-{}'.format(
                mule_alias or random_name.generate_name()
            )
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


class SwarmCaptain(Captain):
    
    compass_cls = SwarmCompass
    
    def __init__(self, section: str):
        
        super().__init__(section)
        LOG.warn("Using Docker Swarm as container manager. This is not recommended for distributed environments")
        self.docker_api = self.docker_compass.get_api()
        self.docker_backend = DockerBackend(logging_level=logging.ERROR)
    
    def run(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, alias: str, foreground=False):
        
        [self.load_vol(v, alias) for v in cargos]
        name = self.with_prefix(alias)
        self.make_name_available(name)
        image = self.docker_backend.ImageClass(img.repo, tag=img.tag)
        
        additional_opts = \
            self.conu_ports(ports) + \
            self.conu_env_vars(env_vars) + \
            self.conu_name(name)
        
        kwargs = dict(
            command=cmd,
            volumes=self.conu_mounts(mounts) + self.conu_vols(cargos),
            additional_opts=additional_opts
        )
        
        if foreground:
            cont = image.run_via_binary_in_foreground(**kwargs)
            self.watch_cont(cont)
        else:
            cont = image.run_via_binary(**kwargs)
        
        return cont
    
    def deploy(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, alias: str, tasks: int = 1):
        
        [self.load_vol(v, alias) for v in cargos]
        self.assert_network()
        name = self.with_prefix(alias)
        depl = self.find_depl(name)
        
        kwargs = dict(
            name=name,
            endpoint_spec=self.swarm_ports(ports),
            networks=[DockerConst.NETWORK],
            mode=ServiceMode('replicated', replicas=tasks),
            task_template=TaskTemplate(
                force_update=5,
                container_spec=ContainerSpec(
                    command=cmd,
                    image=img.target,
                    env=env_vars,
                    mounts=mounts + [v.mount for v in cargos]
                )
            )
        )
        
        if depl is None:
            LOG.debug("Creating container service '{}' with kwargs:".format(name))
            LOG.debug(kwargs)
            return self.docker_api.create_service(**kwargs)
        else:
            kwargs.update(service=depl['ID'], version=depl['Version']['Index'])
            LOG.debug("Updating container service '{}' with kwargs:".format(name))
            LOG.debug(kwargs)
            return self.docker_api.update_service(**kwargs)
    
    def dispose_run(self, alias: str, force=False):
        
        name = self.with_prefix(alias)
        cont = self.find_cont(name)
        
        if cont is not None:
            return self.rm_cont(cont, force=force)
        else:
            return False
    
    def dispose_deploy(self, alias: str, force=False):
        
        name = self.with_prefix(alias)
        return self.rm_depl(name, force=force)
    
    def rm_vol(self, cargo: Cargo, force=False):
        
        try:
            self.docker_api.remove_volume(name=cargo.full_name, force=force)
        except DockerAPIError as e:
            LOG.error(e)
    
    def rm_cont(self, x: DockerContainer, force=False):
        
        try:
            x.kill()
        except DockerAPIError:
            pass
        
        try:
            x.delete(force=force)
        except DockerAPIError as e:
            LOG.error(e)
            return False
        else:
            return True
    
    def rm_depl(self, name: str, force=False):
        
        try:
            self.docker_api.remove_service(name)
        except Exception as e:
            if force:
                LOG.error(e)
                return False
            else:
                raise e
        else:
            return True
    
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
        
    def make_name_available(self, name):
        
        existing = self.find_cont(name)
        
        if existing is not None:
            LOG.warn("Removing old container '{}'".format(name))
            self.rm_cont(existing, force=True)
    
    def watch_cont(self, container: DockerContainer):
        
        try:
            while True:
                if container.is_running():
                    time.sleep(1)
        except (KeyboardInterrupt, InterruptedError):
            self.interrupted = True
    
    def assert_network(self):
        
        nets = self.docker_api.networks(names=[DockerConst.NETWORK])
        
        if len(nets) == 0:
            self.docker_api.create_network(
                name=DockerConst.NETWORK,
                driver="overlay",
                attachable=False,
                scope="global",
                ingress=False
            )  # standard properties for a network that is meant to be used only by Swarm services
        elif len(nets) == 1:
            pass
        else:
            raise NotImplementedError()
    
    def assert_vol(self, cargo: Cargo):
        
        cargo.prefix = self.section
        vols = self.docker_api.volumes(dict(name=cargo.full_name))
        
        if len(vols) == 0:
            self.docker_api.create_volume(name=cargo.full_name)
            
            return True
        elif len(vols) == 1:
            return False
        else:
            return NotImplementedError()
    
    def load_vol(self, cargo: Cargo, mule_alias: str = None):
        
        work_path, mule, error = None, None, None
        self.assert_vol(cargo)
        
        if isinstance(cargo, EmptyCargo) or len(cargo.contents) == 0:
            LOG.debug("Skipping load of volume '{}'".format(cargo.full_name))
            return False
        
        try:
            mule = self.get_mule(cargo, mule_alias)
            self.clear_mule(mule)
            work_path = Workpath.get_tmp()
            cargo.deploy(work_path)
            
            for file_name in os.listdir(work_path):
                self.copy_to(
                    src=work_path.join(file_name),
                    dest=DockerConst.STG_MOUNT,
                    cont=mule
                )
        except Exception as e:
            error = e
        else:
            return True
        finally:
            if work_path is not None:
                work_path.dispose()
            if mule is not None:
                self.rm_cont(mule, force=True)
            if error is not None:
                self.rm_vol(cargo, force=True)
                raise error
    
    def get_mule(self, cargo: Cargo, mule_alias: str = None):
        
        image = self.docker_backend.ImageClass(DockerConst.MULE_IMG)
        
        kwargs = dict(
            name=self.mule_name(mule_alias),
            command=DockerConst.HANG_CMD,
            volumes=[(cargo.full_name, DockerConst.STG_MOUNT, 'rw')]
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
        
        return dict(Ports=[
            dict(PublishedPort=int(p_from), TargetPort=int(p_to), Protocol='tcp')
            for p_from, p_to in [p.split(':') for p in ports]
        ])


class KubeCaptain(Captain):
    
    compass_cls = KubeCompass
    
    def __init__(self, section: str):
        
        super().__init__(section)
        self.namespace = self.captain_compass.get_namespace()
        self.api_key = self.captain_compass.get_api_key()
        self.timeout = self.captain_compass.api_timeout
        self.k8s_backend = K8sBackend(logging_level=logging.ERROR, api_key=self.api_key)
        self.resources = {'resources': self.captain_compass.get_resource_profile(section)}
        self.nfs = self.captain_compass.get_nfs_server(section)
        self.mule = None
    
    def run(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, alias: str, foreground=False):
        
        [self.load_vol(v, alias) for v in cargos]
        name = self.with_prefix(alias)
        self.make_name_available(name)
        vol_refs, vol_defs = self.kube_vols(cargos)
        mount_refs, mount_defs = self.kube_mounts(mounts)
        port_refs, port_defs = self.kube_svc_ports(name, ports)
        
        container = dict(
            name=name,
            image=img.target,
            command=cmd,
            **self.resources,
            volumeMounts=vol_refs + mount_refs,
            env=self.kube_env_vars(env_vars),
            ports=port_refs
        )
        
        template = dict(
            apiVersion="v1",
            kind="Pod",
            metadata=dict(name=name, labels={'app': name}),
            spec={
                'containers': [container],
                'volumes': vol_defs + mount_defs
            }
        )
        
        LOG.info("Creating Pod '{}'".format(name))
        LOG.debug(template)
        
        pod = Pod(namespace=self.namespace, from_template=template)
        self.handle_svc(name, port_defs)
        self.wait_for_pod(pod)
        
        if foreground:
            self.watch_pod(pod)
        
        return pod
    
    def deploy(self, img: ImageSpec, env_vars, mounts, cargos, ports, cmd: list, alias: str, tasks: int = 1):
        
        [self.load_vol(v, alias) for v in cargos]
        name = self.with_prefix(alias)
        vol_refs, vol_defs = self.kube_vols(cargos)
        mount_refs, mount_defs = self.kube_mounts(mounts)
        port_refs, port_defs = self.kube_svc_ports(name, ports)
        
        container = dict(
            name=name,
            image=img.target,
            imagePullPolicy='Always',
            command=cmd,
            **self.resources,
            volumeMounts=vol_refs + mount_refs,
            env=self.kube_env_vars(env_vars),
            ports=port_refs
        )
        
        template = dict(
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
                        'volumes': vol_defs + mount_defs
                    }
                )
            )
        )
        
        if self.find_depl(name) is None:
            LOG.info("Creating deployment '{}'".format(name))
            LOG.debug(template)
            yaml = Kaptan().import_config(template).export(handler='yaml')
            depl = Deployment(namespace=self.namespace, create_in_cluster=True, from_template=yaml)
        else:
            LOG.info("Updating deployment '{}'".format(name))
            LOG.debug(template)
            self.k8s_backend.apps_api.replace_namespaced_deployment(name, self.namespace, template)
            depl = self.find_depl(name)
        
        self.handle_svc(name, port_defs)
        return depl
    
    def dispose_run(self, alias: str, force=False):
        
        name = self.with_prefix(alias)
        self.rm_pod(name, force=force)
        self.rm_svc(name, force=force)
    
    def dispose_deploy(self, alias: str, force=False):
        
        name = self.with_prefix(alias)
        self.rm_depl(name, force=force)
        self.rm_svc(name, force=force)
    
    def rm_vol(self, cargo: Cargo, force=False):
        
        if self.mule is None:
            if force:
                self.prepare_mule()
            else:
                LOG.warn("Missing auxiliary Pod for deletion of volume '{}'".format(cargo.full_name))
                return False
        
        vol_path = os.path.join(DockerConst.STG_MOUNT, cargo.full_name)
        self._exec_in_pod(self.mule, 'rm -rf {}'.format(vol_path))
        return True
    
    def rm_pod(self, name: str, force=False):
        
        extra_kwargs = dict(grace_period_seconds=0) if force else {}
        self.k8s_backend.core_api.delete_namespaced_pod(name=name, namespace=self.namespace, **extra_kwargs)
    
    def rm_depl(self, name: str, force=False):
        
        extra_kwargs = dict(grace_period_seconds=0) if force else {}
        self.k8s_backend.apps_api.delete_namespaced_deployment(name=name, namespace=self.namespace, **extra_kwargs)
    
    def rm_svc(self, name: str, force=False):
        
        extra_kwargs = dict(grace_period_seconds=0) if force else {}
        self.k8s_backend.core_api.delete_namespaced_service(name=name, namespace=self.namespace, **extra_kwargs)
    
    def close(self):
        
        if self.mule is not None:
            self.rm_pod(self.mule.name, force=True)
    
    def _find_sth(self, what, name, method, **kwargs):
        
        return super()._find_sth(
            what=what,
            name=name,
            method=lambda: method(self.namespace).items,
            key=lambda i: i.metadata.name == name
        )
    
    def find_pod(self, name):
        
        return super()._find_sth(
            what='pods',
            method=self.k8s_backend.list_pods,
            name=name,
            namespace=self.namespace
        )
    
    def find_depl(self, name):
        
        return self._find_sth(
            what='deployments',
            method=self.k8s_backend.apps_api.list_namespaced_deployment,
            name=name
        )
    
    def find_svc(self, name):
        
        return self._find_sth(
            what='services',
            method=self.k8s_backend.core_api.list_namespaced_service,
            name=name
        )
    
    def make_name_available(self, name):
        
        existing = self.find_pod(name)
        
        if existing is not None:
            LOG.warn("Removing old pod '{}'".format(name))
            self.rm_pod(existing.name, force=True)
    
    def watch_pod(self, pod: Pod):
        
        logs = self.k8s_backend.core_api.read_namespaced_pod_log(
            name=pod.name,
            namespace=self.namespace,
            follow=True,
            _preload_content=False
        )
        
        try:
            for line in logs:
                LOG.echo(line.decode(Encoding.UTF_8).strip())
        except (KeyboardInterrupt, InterruptedError):
            self.interrupted = True
    
    def wait_for_pod(self, pod: Pod):
        
        for _ in range(self.timeout):
            if pod.get_status().conditions is not None and pod.is_ready():
                return
            else:
                time.sleep(1)
        else:
            raise NhaDockerError("Timed out waiting for pod '{}'".format(pod.name))
    
    def handle_svc(self, name, port_defs):
        
        if self.find_svc(name) is not None:
            LOG.info("Removing old version of service '{}'".format(name))
            self.rm_svc(name)
        
        if len(port_defs) == 0:
            LOG.info('Skipping service creation')
            return
        
        svc = dict(
            apiVersion='v1',
            kind='Service',
            metadata={'name': name},
            spec=dict(
                selector={'app': name},
                type='NodePort',
                ports=port_defs
            )
        )
        
        LOG.info("Creating service '{}'".format(name))
        LOG.debug(svc)
        self.k8s_backend.core_api.create_namespaced_service(self.namespace, svc)
    
    def load_vol(self, cargo: Cargo, mule_alias: str = None):
        
        cargo.prefix = self.section
        work_path, error = None, None
        vol_path = os.path.join(DockerConst.STG_MOUNT, cargo.full_name)
        
        try:
            self.prepare_mule(mule_alias)
            self.clear_mule(self.mule, vol_path)
            work_path = Workpath.get_tmp()
            cargo.deploy(work_path)
            
            for file_name in os.listdir(work_path):
                self.copy_to(
                    src=work_path.join(file_name),
                    dest=vol_path,
                    pod=self.mule
                )
        except Exception as e:
            self.rm_vol(cargo)
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
            command=DockerConst.HANG_CMD,
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
        
        LOG.debug("Creating auxiliar Pod '{}' for handling volumes".format(name))
        LOG.debug(template)
        
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
        
        run_bash_cmd(
            'kubectl cp --namespace={namespace} {src} {pod}:{dest}'.format(
                src=src,
                dest=dest,
                pod=pod.name,
                namespace=self.namespace
            )
        )
    
    def _exec_in_pod(self, pod: Pod, cmd, stderr=True, stdin=False, stdout=True, tty=False):
        
        return stream(
            self.k8s_backend.core_api.connect_get_namespaced_pod_exec,
            name=pod.name, namespace=self.namespace, command=cmd.split(' '),
            stderr=stderr, stdin=stdin, stdout=stdout, tty=tty
        )
    
    def mule_mount(self, mule_name):
        
        cargo = MappedCargo(
            name=mule_name,
            mount_to=DockerConst.STG_MOUNT,
            src=self.nfs['path']
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
            name = cargo.full_name
            
            if isinstance(cargo, MappedCargo):
                nfs_path = cargo.src
            else:
                nfs_path = os.path.join(self.nfs['path'], name)
            
            refs.append(dict(
                name=cargo.full_name,
                mountPath=cargo.mount_to
            ))
            
            defs.append(dict(
                name=cargo.full_name,
                nfs={'server': self.nfs['server'], 'path': nfs_path}
            ))
        
        return refs, defs
    
    def kube_svc_ports(self, name: str, ports: List[str]):
        
        refs, defs = [], []
        cleaner = StructCleaner()
        
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
            defs.append(cleaner({
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


def get_captain(section: str):
    
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
        return capitain_cls(section)
