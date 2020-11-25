**************************
Deploying Noronha
**************************
.. highlight:: none

The following sections intent to show how to install Noronha in production. 
These instructions are focused on a devops team that will deploy and manage Noronha on a Kubernetes-like cluster.

Requirements
================
Minimum:

- Kubernetes cluster (AKS, EKS, GKE, etc.)
    - 3 nodes (2 vCPUs 8GB RAM)
    - 50 GB HDD Disk

- A container registry
- Noronha compatible machine, with kubectl installed


Recomended:

- Kubernetes cluster (AKS, EKS, GKE, etc.)
    - 4 nodes (8 vCPUs 30GB RAM)
    - 250 GB SSD Disk

- A container registry
- Noronha compatible machine, with kubectl installed


Configuring Kubernetes
==========================

You can apply all configurations in this section through kubectl:

.. code-block:: shellscript

    kubectl -n <namespace-id> apply -f <config-file>.yaml


It's recomended to create a namespace for Noronha. You can do this by configuring the following script.

.. code-block:: yaml

    apiVersion: v1
    kind: Namespace
    metadata:
        name: <namespace-id>


Noronha will also need a service account and the permissions to access the cluster. You can create one with the following script.

.. code-block:: yaml

    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: <account-id>
      namespace: <namespace-id>
    ---
    kind: ClusterRole
    apiVersion: rbac.authorization.k8s.io/v1beta1
    metadata: 
      name: <role-id>
      namespace: <namespace-id>
    rules:
    - apiGroups: ["", "extensions", "apps", "autoscaling"]
      resources: ["pods", "services", "deployments", "secrets", "pods/exec", "pods/status", "pods/log", "persistentvolumeclaims", "namespaces", "horizontalpodautoscalers", "endpoints"]
      verbs: ["get", "create", "delete", "list", "update", "watch", "patch"]
    ---
    apiVersion: rbac.authorization.k8s.io/v1beta1
    kind: ClusterRoleBinding
    metadata:
      name: <role-id>
      namespace: <namespace-id>
    subjects:
    - kind: ServiceAccount
      name: <service-account-id>
      namespace: <namespace-id>
    roleRef:
      kind: ClusterRole
      name: <role-id>
      apiGroup: rbac.authorization.k8s.io
    ---
    apiVersion: v1
    kind: Secret
    metadata:
      name: <service-account-id>
      namespace: <namespace-id>
      annotations:
        kubernetes.io/service-account.name: <service-account-id>
    type: kubernetes.io/service-account-token
 

Noronha needs a NFS, which can be deployed in Kubernetes through the script below.

.. code-block:: yaml

    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: <nfs-id>
      namespace: <namespace-id>
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 128Gi
      storageClassName: <storage_class>  # edit the storage class for provisioning disk on demand (Azure: default | Others: standard)
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: <nfs-id>
      namespace: <namespace-id>
    spec:
      selector:
        matchLabels:
          role: <nfs-id>
      template:
        metadata:
          labels:
            role: <nfs-id>
        spec:
          containers:
          - name: <nfs-id>
            image: gcr.io/google_containers/volume-nfs:0.8
            args:
              - /nfs
            ports:
              - name: nfs
                containerPort: 2049
              - name: mountd
                containerPort: 20048
              - name: rpcbind
                containerPort: 111
            securityContext:
              privileged: true
            volumeMounts:
              - mountPath: /nfs
                name: mypvc
          volumes:
            - name: mypvc
              persistentVolumeClaim:
                claimName: <nfs-id>
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: <nfs-id>
      namespace: <namespace-id>
    spec:
      clusterIP: <nfs_server>  # edit the nfs internal ip (if this one is already taken)
      ports:
        - name: nfs
          port: 2049
        - name: mountd
          port: 20048
        - name: rpcbind
          port: 111
      selector:
        role: <nfs-id>



Configuring Noronha client on the machine
=========================================

After the cluster is ready, you need to configure Noronha on your machine.
You may do this by configuring the .nha/nha.yaml file on your home directory.

.. code-block:: yaml

    logger:
      level: DEBUG
      pretty: true
      directory: /logs
      file_name: clever.log
    docker:
      target_registry: <docker_registry>  # edit the docker registry used by the k8s cluster
      registry_secret: <registry_secret>  # edit the name of the k8s secret that holds your docker registry's credentials
    container_manager:
      type: kube
      namespace: clever
      api_timeout: 600
      healthcheck:
        enabled: true
        start_period: 120
        interval: 60
        retries: 12
      storage_class: <storage_class>  # edit the storage class for provisioning disk on demand (Azure: default | Others: standard)
      nfs:
        server: <nfs_server>  # edit the nfs server ip address (same as in nfs.yaml)
        path: /nfs/nha-vols
      resource_profiles:
        nha-train:
          requests:
            memory: 5120
            cpu: 2
          limits:
            memory: 8192
            cpu: 4

You may share this file with other Noronha users as a template for your Noronha cluster.


Deploy Artifactory and Mongo DB
===============================

Noronha may deploy Artifactory and Mongo DB by itself:

.. code-block:: shellscript

    nha get-me-started
