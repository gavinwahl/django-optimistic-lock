django-optimistic-lock
======================

.. image:: https://secure.travis-ci.org/gavinwahl/django-optimistic-lock.png?branch=master
   :target: https://travis-ci.org/gavinwahl/django-optimistic-lock

Implements an offline optimistic lock [1]_ for Django models. Requires
Django 1.6, because model saving was recently refactored to allow access
to the update query [2]_.


Usage
-----

Add a ``VersionField`` and inherit from ``VersionedMixin``.

.. code-block:: python

    from ool import VersionField, VersionedMixin

    class MyModel(VersionedMixin, models.Model):
        version = VersionField()


Whenever ``MyModel`` is saved, the version will be checked to ensure
the instance has not changed since it was last fetched. If there is a
conflict, a ``ConcurrentUpdate`` exception will be raised.

Implementation
--------------
A ``VersionField`` is just an integer that increments itself every
time its model is saved. ``VersionedMixin`` overrides ``_do_update``
(which is called by ``save`` to actually do the update) to add an extra
condition to the update query -- that the version in the database is
the same as the model's version. If they match, there have been no
concurrent modifications. If they don't match, the UPDATE statement will
not update any rows, and we know that someone else saved first.

This produces SQL that looks something like::

    UPDATE mymodel SET version = version + 1, ... WHERE id = %s AND version = %s

When no rows were updated, we know someone else won and we need to raise
a ``ConcurrentUpdate``.


Comparison to ``django-concurrency``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
`django-concurrency <https://github.com/saxix/django-concurrency>`_
uses ``SELECT FOR UPDATE`` to implement the version checking. I wanted
to avoid database-level locking, so ``django-optimistic-lock`` adds a
version filter to the update statement, as described by Martin Fowler
[1]_.

Running the tests
-----------------
::

    make test


.. [1] http://martinfowler.com/eaaCatalog/optimisticOfflineLock.html
.. [2] https://code.djangoproject.com/ticket/16649
