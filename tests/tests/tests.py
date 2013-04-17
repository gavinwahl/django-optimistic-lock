from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django import forms
from django.test.client import Client
from django import db
from django.db import transaction
from django.utils.unittest import skipIf, expectedFailure

from ool import ConcurrentUpdate

from .models import (SimpleModel, ProxyModel, InheritedModel,
                     InheritedVersionedModel, ImproperlyConfiguredModel,
                     CounterModel, ConcreteModel)


def refetch(model_instance):
    """
    Gets a fresh model instance from the database
    """
    return model_instance.__class__.objects.get(pk=model_instance.pk)


class OolTests(TestCase):
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
            x.save()
        self.assertEqual(refetch(x).name, 'foo')

    def test_version_matches_after_insert(self):
        x = SimpleModel(name='foo')
        x.save()
        self.assertEqual(x.version, refetch(x).version)

    def test_simple(self):
        self.normal(SimpleModel)
        self.conflict(SimpleModel)
        self.update_fields_doesnt_update(SimpleModel)
        self.update_fields_still_checks(SimpleModel)

    def test_proxy(self):
        self.normal(ProxyModel)
        self.conflict(ProxyModel)
        self.update_fields_doesnt_update(ProxyModel)
        self.update_fields_still_checks(ProxyModel)

    def test_inheritance(self):
        self.normal(InheritedModel)
        self.conflict(InheritedModel)
        self.update_fields_doesnt_update(InheritedModel)
        self.update_fields_still_checks(InheritedModel)

    def test_unversioned_parent(self):
        self.normal(InheritedVersionedModel)
        self.conflict(InheritedVersionedModel)
        self.update_fields_doesnt_update(InheritedVersionedModel)

    # can not be fixed until django #20272 is
    @expectedFailure
    def test_unversioned_parent_fields(self)
        self.update_fields_still_checks(InheritedVersionedModel)

    def test_abstract(self):
        self.normal(ConcreteModel)
        self.conflict(ConcreteModel)
        self.update_fields_doesnt_update(ConcreteModel)
        self.update_fields_still_checks(ConcreteModel)

    @expectedFailure
    def test_defer(self):
        x = SimpleModel.objects.create(name='foo')
        y = SimpleModel.objects.defer('version').get(pk=x.pk)
        x.save()
        with self.assertRaises(ConcurrentUpdate):
            y.save()

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
            SimpleModel._meta.get_field_by_name('version')[0],
            SimpleModel().get_version_field()
        )

        with self.assertRaises(ImproperlyConfigured):
            ImproperlyConfiguredModel().get_version_field()


class SimpleForm(forms.ModelForm):
    class Meta:
        model = SimpleModel


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
        self.assertIn(
            '<input id="id_version" name="version" type="hidden" value="0"',
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

        self.assertIn(
            b'<input id="id_version" name="version" readonly="readonly" type="text" value="0"',
            resp.content
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
                    db.close_connection()
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
