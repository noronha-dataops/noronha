.. highlight:: none
.. _configuration-guide:

*******************
Configuring Noronha
*******************

Configuration Files
===================
Noronha's default configuration file is packaged together with its Python libraries, under the `resources directory <https://gitlab.eva.bot/asseteva/noronha-dataops/tree/master/noronha/resources>`_. It's a YAML file in which the top keys organize properties according to the subjects they refer to.

.. literalinclude:: ../../../noronha/resources/nha.yaml

This configuration can be extended by placing a *nha.yaml* file with the desired keys in the current working directory or in the user's home directory at *~/.nha/*. The file resolution is as follows:

- **./nha.yaml**: if present, this file will be used to extend the default configuration. No other files will be looked for.

- **~/.nha/nha.yaml**: if the previous alternative wasn't available, this file will be used instead.

- If none of the alternatives above was available, only the default configuration is going to be used.

.. _island-conventions:

Conventions for Islands
=======================
The following properties are common for all :ref:`plugins <island-concepts>`.

- **native:** (boolean) If true, this plugin runs inside a container manager by Noronha. Otherwise, this plugin runs in a dedicated server, managed by the user or a third-party. The later option is referred to as *foreign mode*, in opposition to the *native mode* (default: true).

- **host:** This property is only used in *foreign mode*. It refers to the hostname or IP of the server in which Noronha is going to find the service (e.g.: MongoDB's hostname or IP, as it appears in its connection string).

- **port:** In *foreign mode*, this refers to the port in which the plugin is exposed (e.g.: MongoDB's port, as it appears in its connection string). In *native mode*, this refers to the server port in which Noronha is going to expose the plugin. Note that if your container manager is Kubernetes only the ports between 30000 and 31000 are available.

- **user:** Username for authenticating in the plugin (*foreign mode* only).

- **pswd:** Password for authenticating in the plugin (*foreign mode* only).

- **tchest:** Instead of specifying credentials explicitly, you may set this property with the name of a :ref:`Treasure Chest <tchest-usage>` that holds your pre-recorded credentials.

- **disk_allocation_mb:** This property is only used in *native mode*. When Noronha creates a volume to store the plugin's data, it's going to ask the container manager for this amount of storage, in megabytes.

The following topics describe the properties under each configuration subject (top keys in the YAML file).

Router
======
The following properties are found under the key *router* and they refer to how Noronha uses its model router.

- **port:** As explained in the :ref:`island conventions <island-conventions>` (default: 30080).

MongoDB
=======
The following properties are found under the key *mongo* and they refer to how Noronha uses its database.

- **port:** As explained in the :ref:`island conventions <island-conventions>` (default: 30017).

- **database:** Name of the database that Noronha is going to access in MongoDB. Created in runtime if not existing (default: nha_db).

- **write_concern:** Dictionary with the concern options that Noronha should use when writing to the database, as in `MongoDB's manual <https://docs.mongodb.com/manual/reference/write-concern/>`_. The following example represents the default values for this property:

.. parsed-literal::

    write_concern:
      w: 1
      j: true
      wtimeout: 5

File Manager
============
The following properties are found under the key *file_manager* and they refer to how Noronha uses its file manager.

- **port:** As explained in the :ref:`island conventions <island-conventions>` (default: 30023).

- **use_ssl:** (boolean) Set to true if your file manager server uses https (*foreign mode* only) (default: false).

- **check_certificate:** (boolean) When using SSL encryption, you may set this to false in order to skip the verification of your server's certificate, although this is not recommended (*foreign mode* only) (default: true).

- **type:** Reference to the file manager that Noronha should use (either *artif*, for Artifactory, or *nexus*, for Nexus) (default: artif).

- **repository:** Name of an existing repository that Noronha should use to store its model files, datasets and output notebooks. For Artifactory, the default is *example-repo-local*. For Nexus there is no default value, since the first repository needs to be created manually through the plugin's user interface.

Project
=======
The following properties are found under the key *project* and they refer to how Noronha handle's your project.

- **working_project:** this tells the framework which project you are working on right now. This is important because many features such as training or deploying models can only be performed inside the scope of a project. However, before looking into this property the framework checks two other alternatives: was a project name provided as argument to the function? Is the current working directory a local repository for a project?

Logger
======
The following properties are found under the key *logger* and they refer to how Noronha logs messages.

- **level:** Log verbosity level, as in Python's logging (one of: ERROR, WARN, INFO, DEBUG) (default: INFO).

- **pretty:** (boolean) If true, all dictionaries and exception objects are pretty-printed (default: false).

- **directory:** Path to the directory where log files hould be kept (default: ~/.nha/logs/)

- **file_name:** Log file name (default: noronha.log)

- **max_bytes:** Max log file size, in bytes (default: 1mb).

- **bkp_count:** Number of log file backups to be kept (default: 1).

- **join_root:** (boolean) If true, log messages by other frameworks such as Flask and Conu are also dumped to Noronha's log file.

Docker
======
The following properties are found under the key *docker* and they refer to how Noronha uses the Docker engine.

- **daemon_address:** Path or address to Docker daemon's socket (default: unix:/var/run/docker.sock).

- **target_registry:** Address of the Docker registry to which the images built by the framework will be uploaded (default is null, so images are kept locally).

The following parameters are only used if the chosen container manager is Kubernetes:

- **registry_secret:** Name of the Kubernetes secret that your cluster uses to access the registry configured in the previously. This property is recommended if your containers fail with the message *ImagePullBackOff*.

Container Manager
=================
The following properties are found under the key *container_manager* and they refer to how Noronha uses the container manager.

- **type:** Reference to the container manager that Noronha should use as its backend (either *swarm*, for Docker Swarm, or *kube*, for Kubernetes) (default: swarm).

- **api_timeout:** The maximum time, in seconds, to wait before the container manager completes a requested action (default: 20 for Docker Swarm, 60 for Kubernetes).

- **resource_profiles:** A mapping in which the keys are resource profile names and the values are resource specifications. Example:

.. parsed-literal::

    light_training:
      requests:
        memory: 256
        cpu: 1
      limits:
        memory: 512
        cpu: 2

    heavy_training:
      requests:
        memory: 2048
        cpu: 2
      limits:
        memory: 4096
        cpu: 4

    # keeping compatibility with both Kubernetes and Docker Swarm,
    # all *cpu* values are expressed in **vCores** and *memory* in **MB**.

Such resource profile names may be specified when starting an IDE, training or deployment (note that when deploying with multiple replicas, the resources specification will be applied to each replica).

Another interesting strategy is to specify default resource profiles according to the *work section*. The available work sections are *nha-ide*, *nha-train* and *nha-depl*. Those refer to the default resource specifications applied when using the IDE, training or running a deploy, respectively. Example:

.. parsed-literal::

    nha-ide:
      requests:
        memory: 256
        cpu: 1
      limits:
        memory: 512
        cpu: 2

    nha-train:
      requests:
        memory: 2048
        cpu: 2
      limits:
        memory: 4096
        cpu: 4

The following parameters are only used if the chosen container manager is Kubernetes:

- **namespace:** An existing Kubernetes namespace in which Noronha will create its resources (default: default).

- **storage_class:** An existing storage class that Noronha will use to create persistent volume claims for storing its plugins' data (default: standard).

- **nfs:** A mapping with the keys *path* and *server*. The key *server* should point to your NFS server's hostname or IP, whereas *path* refers to an existing directory inside your NFS server. Noronha will create volumes under the specified directory for sharing files with its training, deployment and IDE containers.
