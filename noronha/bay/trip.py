# -*- coding: utf-8 -*-

"""This module handles container executions (i.e.: 'fire-and-forget' processes)

In this scope a container execution may be:
 - a simple docker container execution (if container manager is 'swarm')
 - a simple K8s' pod with no replication (if container manager is 'kube')
"""


