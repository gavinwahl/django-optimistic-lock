from unittest import skipIf

from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.test.client import Client
from django import db
from django.db import transaction

from ool import ConcurrentUpdate

from .models import (SimpleModel, ProxyModel, InheritedModel,
                     InheritedVersionedModel, ImproperlyConfiguredModel,
                     CounterModel, ConcreteModel)
from .forms import SimpleForm


def refetch(model_instance):
    """
    Gets a fresh model instance from the database
    """
    return model_instance.__class__.objects.get(pk=model_instance.pk)


class OolTests(TestCase):
    def different_creation_ways(self, model):
        # Create object using the default Manager's create method
        x = model.objects.create(name='baz')
        self.assertTrue(refetch(x).name == 'baz')
        x.delete()

        # Create object as a fresh Model instance rather than using Manager's create method
        x = model(name='baz')
        x.save()
        self.assertTrue(refetch(x).name == 'baz')
        x.delete()

        # Create object with preset PK value
        x = model(id=10, name='baz')
        x.save()
        y = refetch(x)
        self.assertTrue(y.name == 'baz')
        self.assertTrue(y.id == 10)
        x.delete()

        # Create object using default Manger's create method and preset PK value
        x = model.objects.create(id=10, name='foo')
        y = refetch(x)
        self.assertTrue(y.name == 'foo')
        self.assertTrue(y.id == 10)
        x.delete()

    def normal(self, model):
        x = model.objects.create(name='foo')
        self.assertTrue(refetch(x).name == 'foo')

        x.name = 'bar'
        x.save()

        self.assertTrue(refetch(x).name == 'bar')

    def conflict(self, model):
        x = model.objects.create(name='foo')

        # conflicting update
        y = refetch(x)
        y.save()

        with self.assertRaises(ConcurrentUpdate):
            with transaction.atomic():
                x.save()
        self.assertEqual(refetch(x).name, 'foo')

    def test_version_matches_after_insert(self):
        x = SimpleModel(name='foo')
        x.save()
        self.assertEqual(x.version, refetch(x).version)

    def test_simple(self):
        self.different_creation_ways(SimpleModel)
        self.normal(SimpleModel)
        self.conflict(SimpleModel)
        self.update_fields_doesnt_update(SimpleModel)
        self.update_fields_still_checks(SimpleModel)

    def test_proxy(self):
        self.different_creation_ways(ProxyModel)
        self.normal(ProxyModel)
        self.conflict(ProxyModel)
        self.update_fields_doesnt_update(ProxyModel)
        self.update_fields_still_checks(ProxyModel)

    def test_inheritance(self):
        self.different_creation_ways(InheritedModel)
        self.normal(InheritedModel)
        self.conflict(InheritedModel)
        self.update_fields_doesnt_update(InheritedModel)
        self.update_fields_still_checks(InheritedModel)

    def test_unversioned_parent(self):
        self.different_creation_ways(InheritedVersionedModel)
        self.normal(InheritedVersionedModel)
        self.conflict(InheritedVersionedModel)
        self.update_fields_doesnt_update(InheritedVersionedModel)

    def test_unversioned_parent_fields(self):
        self.update_fields_still_checks(InheritedVersionedModel)

    def test_abstract(self):
        self.different_creation_ways(ConcreteModel)
        self.normal(ConcreteModel)
        self.conflict(ConcreteModel)
        self.update_fields_doesnt_update(ConcreteModel)
        self.update_fields_still_checks(ConcreteModel)

    def test_defer_version(self):
        """
        It doesn't make sense to save after deferring version
        """
        x = SimpleModel.objects.create(name='foo')
        x = SimpleModel.objects.defer('version').get(pk=x.pk)
        with self.assertRaises(RuntimeError):
            x.save()

    def test_defer_otherwise(self):
        """
        We should be able to defer fields other than version
        """
        x = SimpleModel.objects.create(name='foo')
        x = SimpleModel.objects.defer('name').get(pk=x.pk)
        x.save()

    def update_fields_doesnt_update(self, model):
        """
        Calling save with update_fields not containing version doesn't update
        the version.
        """
        x = model.objects.create(name='foo')
        y = refetch(x)

        y.name = 'bar'
        # bypass versioning by only updating a single field
        y.save(update_fields=['name'])
        # The version on the instance of y should match the database version.
        # This allows y to be saved again.
        self.assertEqual(refetch(y).version, y.version)

        x.save()
        self.assertEqual(refetch(x).name, 'foo')

    def update_fields_still_checks(self, model):
        """
        Excluding the VersionField from update_fields should still check
        for conflicts.
        """
        x = model.objects.create(name='foo')
        y = refetch(x)
        x.save()
        y.name = 'bar'
        with self.assertRaises(ConcurrentUpdate):
            y.save(update_fields=['name'])

    def test_get_version_field(self):
        self.assertEqual(
            SimpleModel._meta.get_field('version'),
            SimpleModel().get_version_field()
        )

        with self.assertRaises(ImproperlyConfigured):
            ImproperlyConfiguredModel().get_version_field()


class FormTests(TestCase):
    def setUp(self):
        self.obj = SimpleModel.objects.create(name='foo')

    def test_conflict(self):
        form = SimpleForm(instance=self.obj)
        form = SimpleForm(data=form.initial, instance=self.obj)

        refetch(self.obj).save()

        with self.assertRaises(ConcurrentUpdate):
            form.save()

    def test_tampering(self):
        """
        When messing with the version in the form, an exception should be
        raised
        """
        form = SimpleForm(instance=self.obj)
        data = form.initial
        data['version'] = str(int(data['version']) + 1)
        form = SimpleForm(data=data, instance=self.obj)

        with self.assertRaises(ConcurrentUpdate):
            form.save()

    def test_omit(self):
        form = SimpleForm(instance=self.obj)
        data = form.initial
        del data['version']
        form = SimpleForm(data=data, instance=self.obj)
        self.assertFalse(form.is_valid())

    def test_field_is_hidden(self):
        form = SimpleForm(instance=self.obj)
        self.assertInHTML(
            '<input type="hidden" name="version" value="0" id="id_version">',
            form.as_p()
        )

    def test_actually_works(self):
        form = SimpleForm(instance=self.obj)
        data = form.initial
        data['name'] = 'bar'
        form = SimpleForm(data=data, instance=self.obj)
        self.obj = form.save()
        self.assertEqual(self.obj.name, 'bar')

    def test_admin(self):
        """
        VersionFields must be rendered as a readonly text input in the admin.
        """
        from django.contrib.auth.models import User
        User.objects.create_superuser(
            username='foo',
            password='foo',
            email='foo@example.com'
        )
        c = Client()
        c.login(username='foo', password='foo')
        resp = c.get(
            reverse('admin:tests_simplemodel_change', args=(self.obj.pk,))
        )

        self.assertInHTML(
            '<input type="text" name="version" value="0" readonly="readonly" required id="id_version">',
            resp.content.decode()
        )


def test_concurrently(times):
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """
    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []
            import threading

            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception as e:
                    exceptions.append(e)
                    raise
                finally:
                    db.close_old_connections()
            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception(
                    'test_concurrently intercepted %s exceptions: %s' %
                    (len(exceptions), exceptions))
        return wrapper
    return test_concurrently_decorator


class ThreadTests(TransactionTestCase):
    @skipIf(db.connection.vendor == 'sqlite',
            "in-memory sqlite db can't be used between threads")
    def test_threads(self):
        """
        Run 25 threads, each incrementing a shared counter 5 times.
        """

        obj = CounterModel.objects.create()
        transaction.commit()

        @test_concurrently(25)
        def run():
            for i in range(5):
                while True:
                    x = refetch(obj)
                    transaction.commit()
                    x.count += 1
                    try:
                        x.save()
                        transaction.commit()
                    except ConcurrentUpdate:
                        # retry
                        pass
                    else:
                        break
        run()

        self.assertEqual(refetch(obj).count, 5 * 25)
