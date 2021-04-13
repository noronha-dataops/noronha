*********************
Modules Reference
*********************
.. highlight:: none

This section summarizes the roles and responsibilities of the most important modules inside Noronha's software architecture.

db
==
The following topics describe the modules inside the package `noronha.db <https://github.com/noronha-dataops/noronha/tree/master/noronha/db>`_,
which is responsible for defining the ORM's for all metadata objects managed by Noronha,
as well as utilities for handling those objects.

:main.py:

.. automodule:: noronha.db.main

:utils.py:

.. automodule:: noronha.db.utils

:proj.py:

.. automodule:: noronha.db.proj

:bvers.py:

.. automodule:: noronha.db.bvers

:model.py:

.. automodule:: noronha.db.model

:ds.py:

.. automodule:: noronha.db.ds

:train.py:

.. automodule:: noronha.db.train

:movers.py:

.. automodule:: noronha.db.movers

:depl.py:

.. automodule:: noronha.db.depl

:tchest.py:

.. automodule:: noronha.db.tchest

bay
===
The following topics describe the modules inside the package `noronha.bay <https://github.com/noronha-dataops/noronha/tree/master/noronha/bay>`_,
which provides interfaces that help Noronha interact with other systems such as container managers and file managers.
Note that every module inside this package has a nautic/pirate-like thematic.

:warehouse.py:

.. automodule:: noronha.bay.warehouse

:barrel.py:

.. automodule:: noronha.bay.barrel

:cargo.py:

.. automodule:: noronha.bay.cargo

:captain.py:

.. automodule:: noronha.bay.captain

:expedition.py:

.. automodule:: noronha.bay.expedition

:island.py:

.. automodule:: noronha.bay.island

:compass.py:

.. automodule:: noronha.bay.compass

:tchest.py:

.. automodule:: noronha.bay.tchest

:anchor.py:

.. automodule:: noronha.bay.anchor

:shipyard.py:

.. automodule:: noronha.bay.shipyard
