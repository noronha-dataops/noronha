*************
CLI Reference
*************
.. highlight:: none

This section describes the usage of Noronha's command line interface.
Each topic in this section refers to a different API subject such as projects, models and so on.

General
=======
The entrypoint for Noronha's CLI is either the keyword *noronha*, for being explicit, or the alias *nha*,
for shortness and cuteness. You can always check which commands are available with the *help* option::

    nha --help  # overview of all CLI subjects
    nha proj --help  # describe commands under the subject *proj*
    nha proj new --help  # details about the command *new* under the subject *proj*

Note that the Conda environment in which you :ref:`installed <installation-intro>` Noronha
needs to be activated so that this entrypoint is accessible. Besides, we assume these
commands are executed from the :ref:`host machine <orchestration-concepts>`.

The entrypoint also accepts the following flags and options for customizing a command's output::

    -l, --log-level TEXT  Level of log verbosity (DEBUG, INFO, WARN, ERROR)
    -d, --debug           Set log level to DEBUG
    -p, --pretty          Less compact, more readable output
    -s, --skip-questions  Skip questions
    -b, --background      Run in background, only log to files

Usage example for skipping questions in background and keeping only pretty warning messages in the log files:

.. parsed-literal::

    nha --background --skip-questions --log-level WARN --pretty proj list
    nha -b -s -l WARN -p proj list  # same command, shorter version with aliases

The default directory for log files is **~/.nha/logs**. For further log configuration options see the :ref:`log configuration section <log-configuration>`.

There's also a special command for *newbies*, that's accesible directly from the entrypoint::

    nha get-me-started

As stated in the :ref:`introduction <installation-intro>`, this is going to configure the
basic :ref:`plugins <island-concepts>` in native mode automatically. This means that after
running this command your :ref:`container manager <orchestration-concepts>` is going to be
running a MongoDB service for storing Noronha's :ref:`metadata <data-model-guide>` and an
Artifactory service for managing Noronha's files. This is useful if you are just
experimenting with the framework and do not want to spend time customizing anything yet.

Project
=======
Reference for commands under the subject *proj*.

- **info:** information about a project

.. parsed-literal::

    --proj, --name    Name of the project (default: current working project)

- **list:** list hosted projects

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields
    -m, --model     Only projects that use this model will be listed

- **rm:** remove a project and everything related to it

.. parsed-literal::

    --proj, --name    Name of the project (default: current working project)

- **new:** host a new project in the framework

.. parsed-literal::

    -n, --name       Name of the project
    -d, --desc       Free text description
    -m, --model      Name of an existing model (further info: nha model --help)
    --home-dir       Local directory where the project is hosted.
                     Example: /path/to/proj
    --git-repo       The project's remote Git repository.
                     Example: https://<git_server>/<proj_repo>
    --docker-repo    The project's remote Docker repository.
                     Example: <docker_registry>/<proj_image>

- **update:** update a projects in the database

.. parsed-literal::

    -n, --name       Name of the project you want to update (default: current working project)
    -d, --desc       Free text description
    -m, --model      Name of an existing model (further info: nha model --help)
    --home-dir       Local directory where the project is hosted.
                     Example: /path/to/proj
    --git-repo       The project's remote Git repository.
                     Example: https://<git_server>/<proj_repo>
    --docker-repo    The project's remote Docker repository.
                     Example: <docker_registry>/<proj_image>

.. _build-command:

- **build:** encapsulate the project in a new Docker image

.. parsed-literal::

    --proj         Name of the project (default: current working project)
    -t, --tag      Docker tag for the image (default: latest)
    --no-cache     Flag: slower build, but useful when the cached layers contain outdated information
    --from-here    Flag: build from current working directory (default option)
    --from-home    Flag: build from project's home directory
    --from-git     Flag: build from project's Git repository (master branch)
    --pre-built    Flag: don't build, just pull and tag a pre-built image from project's Docker repository


Build Version
=============
Reference for commands under the subject *bvers*.

- **info:** information about a build version

.. parsed-literal::

    --proj    The project to which this build version belongs (default: current working project)
    --tag     The build version's docker tag (default: latest)

- **list:** list build versions

.. parsed-literal::

    --proj          The project whose versions you want to list (default: current working project)
    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields

- **rm:** remove a build version

.. parsed-literal::

    --proj    The project in which this version belongs (default: current working project)
    --tag     The version's docker tag (default: latest)

Model
=====
Reference for commands under the subject *model*.

- **info:** information about a model

.. parsed-literal::

    --name    Name of the model

- **list:** list model records

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields

- **rm:** remove a model along with all of it's versions and datasets

.. parsed-literal::

    -n, --name    Name of the model

- **new:** record a new model in the database

.. parsed-literal::

    -n, --name      Name of the model
    -d, --desc      Free text description
    --model-file    JSON describing a file that is used for saving/loading this model.
                    Example:
                    {"name": "categories.pkl", "desc": "Pickle with DataFrame for looking up prediction labels", "required": true, "max_mb": 64}
    --data-file     JSON describing a file that is used for training this model.
                    Example:
                    {"name": "intents.csv", "desc": "CSV file with examples for each user intent", "required": true, "max_mb": 128}

- **update:** update a model record

.. parsed-literal::

    -n, --name          Name of the model you want to update
    -d, --desc          Free text description
    --model-file        JSON describing a file that is used for saving/loading this model.
                        Example:
                        {"name": "categories.pkl", "desc": "Pickle with DataFrame for looking up prediction labels", "required": true, "max_mb": 64}
    --data-file         JSON describing a file that is used for training this model.
                        Example:
                        {"name": "intents.csv", "desc": "CSV file with examples for each user intent", "required": true, "max_mb": 128}
    --no-model-files    Flag: disable the tracking of model files
    --no-ds-files       Flag: disable the tracking of dataset files

Dataset
=======
Reference for commands under the subject *ds*.

- **info:** information about a dataset

.. parsed-literal::

    --model    Name of the model to which this dataset belongs
    --name     Name of the dataset

- **list:** list datasets

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields
    --model         Only datasets that belong to this model will be listed

- **rm:** remove a dataset and all of its files

.. parsed-literal::

    --model    Name of the model to which this dataset belongs
    --name     Name of the dataset

- **new:** add a new dataset

.. parsed-literal::

    -n, --name       Name of the dataset (defaults to a random name)
    -m, --model      The model to which this dataset belongs (further info: nha model --help)
    -d, --details    JSON with any details related to the dataset
    -p, --path       Path to the directory that contains the dataset files (default: current working directory)

- **update:** update a dataset's details or files

.. parsed-literal::

    -n, --name       Name of the dataset you want to update
    -m, --model      The model to which this dataset belongs (further info: nha model --help)
    -d, --details    JSON with details related to the dataset
    -p, --path       Path to the directory that contains the dataset files (default: current working directory)

Training
========
Reference for commands under the subject *train*.

- **info:** information about a training execution

.. parsed-literal::

    --name    Name of the training
    --proj    Name of the project responsible for this training (default: current working project)

- **list:** list training executions

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields
    --proj          Name of the project responsible for the trainings (default: current working project)

- **rm:** remove a training's metadata

.. parsed-literal::

    --name    Name of the training
    --proj    Name of the project responsible for this training (default: current working project)

- **new:** execute a new training

.. parsed-literal::

    --name                Name of the training (defaults to a random name)
    --proj                Name of the project responsible for this training (default: current working project)
    --notebook, --nb      Relative path, inside the project's directory
                          structure, to the notebook that will be executed
    -p, --params          JSON with parameters to be injected in the notebook
    -t, --tag             The training runs on top of a Docker image that
                          belongs to the project. You may specify the image's
                          Docker tag or let it default to "latest"
    -e, --env-var         Environment variable in the form KEY=VALUE
    -m, --mount           A host path or docker volume to mount on the training container.
                          Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>
                          Example: /home/user/data:/data:rw
    --dataset, --ds       Reference to a dataset to be mounted on the training container.
                          Syntax: <model_name>:<dataset_name>
                          Example: iris-clf:iris-data-v0
    --pretrained          Reference to a model version that will be used as a pre-trained model during this training.
                          Syntax: <model_name>:<version_name>
                          Example: word2vec:en-us-v1
    --resource-profile    Name of a resource profile to be applied for each container.
                          This profile should be configured in your nha.yaml file

Model Version
=============
Reference for commands under the subject *movers*.

- **info:** information about a model version

.. parsed-literal::

    --model    Name of the model to which this version belongs
    --name     Name of the version

- **list:** list model versions

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields
    --model         Only versions of this model will be listed
    --dataset       Only versions trained with this dataset will be listed
    --train         Only model versions produced by this training will be listed
    --proj          To be used along with 'train': name of the project to which this training belongs

- **rm:** remove a model version and all of its files

.. parsed-literal::

    --model    Name of the model to which this version belongs
    --name     Name of the version

- **new:** record a new model version in the framework

.. parsed-literal::

    -n, --name       Name of the version (defaults to a random name)
    -m, --model      The model to which this version belongs (further info: nha model --help)
    -d, --details    JSON with details related to the model version
    -p, --path       Path to the directory that contains the model files (default: current working directory)
    --dataset        Name of the dataset that trained this model version
    --train          Name of the training that produced this model version
    --proj           To be used along with 'train': name of the project to
                     which this training belongs

- **update:** update a model version's details or files

.. parsed-literal::

    -n, --name       Name of the model version you want to update
    -m, --model      The model to which this version belongs (further info: nha model --help)
    -d, --details    JSON with details related to the version
    -p, --path       Path to the directory that contains the model files (default: current working directory)
    --dataset        Name of the dataset that trained this model version
    --train          Name of the training that produced this model version
    --proj           To be used along with 'train': name of the project to which this training belongs

Deployment
==========
Reference for commands under the subject *depl*.

- **info:** information about a deployment

.. parsed-literal::

    --name    Name of the deployment
    --proj    Name of the project responsible for this deployment (default: current working project)

- **list:** list deployments

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields
    --proj          Name of the project responsible for this deployment (default: current working project)

- **rm:** remove a deployment

.. parsed-literal::

    --name    Name of the deployment
    --proj    Name of the project responsible for this deployment (default: current working project)

- **new:** setup a deployment

.. parsed-literal::

    --name                Name of the deployment (defaults to a random name)
    --proj                Name of the project responsible for this deployment (default: current working project)
    --notebook, --nb      Relative path, inside the project's directory
                          structure, to the notebook that will be executed
    -p, --params          JSON with parameters to be injected in the notebook
    -t, --tag             Each deployment task runs on top of a Docker image
                          that belongs to the project. You may specify the
                          image's Docker tag or let it default to "latest"
    -n, --n-tasks         Number of tasks (containers) for deployment
                          replication (default: 1)
    -p, --port            Host port to be routed to each container's inference
                          service
    -e, --env-var         Environment variable in the form KEY=VALUE
    -m, --mount           A host path or docker volume to mount on each deployment container.
                          Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>
                          Example: /home/user/data:/data:rw
    --movers, --mv        Reference to a model version to be mounted on each deployment container.
                          Syntax: <model_name>:<version_name>
                          Example: iris-clf:experiment-v1
    --resource-profile    Name of a resource profile to be applied for each container.
                          This profile should be configured in your nha.yaml file


Notebook (IDE)
==============
You can start-up a Jupyter notebook interface for your project in order to edit and test your code inside a
disposable environment that is much like the environment your code is going to find in production.

- **note:** Access to an interactive notebook (IDE)

.. parsed-literal::

    -t, --tag             The IDE runs on top of a Docker image that belongs to the current working project.
                          You may specify the image's Docker tag or let it default to "latest"
    -p, --port            Host port that will be routed to the notebook's user interface (default: 30088)
    -e, --env-var         Environment variable in the form KEY=VALUE
    -m, --mount           A host path or docker volume to mount on the IDE's container.
                          Syntax: <host_path_or_volume_name>:<container_path>:<rw/ro>
                          Example: /home/user/data:/data:rw
    --edit                Flag: also mount current directory into the container's /app directory.
                          This is useful if you want to edit code, test it and save it in the local machine
                          (WARN: in Kubernetes mode this will only work if the current directory is part of your NFS server)
    --dataset, --ds       Reference to a dataset to be mounted on the IDE's container.
                          Syntax: <model_name>:<dataset_name>
                          Example: iris-clf:iris-data-v0
    --movers, --mv        Reference to a model version to be mounted on the IDE's container.
                          Syntax: <model_name>:<version_name>
                          Example: word2vec:en-us-v1:true
    --resource-profile    Name of a resource profile to be applied for each container.
                          This profile should be configured in your nha.yaml file


Islands (Plugins)
=================
Under the subject *isle* there is a branch of commands for each :ref:`plugin <island-concepts>`.
You can check a plugin's commands with the *help* option:

.. parsed-literal::

    nha isle *plugin* --help  # overview of this plugin's commands
    nha isle *plugin* *command* --help  # details about one of this plugin's commands

The available :ref:`plugins <island-concepts>` are:

.. parsed-literal::

    artif   File manager
    mongo   Database for metadata
    nexus   File manager (alternative)
    router  (Optional) Routes requests to deployments

The commands bellow are available for all :ref:`plugins <island-concepts>`, unless stated otherwise:

- **setup:** start and configure this plugin

.. parsed-literal::

    -s, --skip-build    Flag: assume that the required Docker image for setting up
                        this plugin already exists.

.. _tchest-usage:

Treasure Chest
==============
Reference for commands under the subject *tchest*, which are meant to manage :ref:`Treasure Chests <tchest-doc>`.

- **info:** information about a Treasure Chest

.. parsed-literal::

    --name    Name of the Treasure Chest

- **list:** list Treasure Chest records

.. parsed-literal::

    -f, --filter    Query in MongoDB's JSON syntax
    -e, --expand    Flag: expand each record's fields

- **rm:** remove a Treasure Chest

.. parsed-literal::

    -n, --name    Name of the Treasure Chest

- **new:** record a new Treasure Chest in the database

.. parsed-literal::

    -n, --name      Name of the Treasure Chest
    --desc          Free text description
    --details       JSON with any details related to the Treasure Chest
    -u, --user      Username to be recorded
    -p, --pswd      Password to be recorded

- **update:** update a Treasure Chest

.. parsed-literal::

    -n, --name      Name of the Treasure Chest you want to update
    --desc          Free text description
    --details       JSON with any details related to the Treasure Chest
    -u, --user      Username to be recorded
    -p, --pswd      Password to be recorded
