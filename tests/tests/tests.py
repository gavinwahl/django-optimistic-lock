from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured

from ool import ConcurrentUpdate

from .models import (SimpleModel, ProxyModel, InheritedModel,
                     InheritedVersionedModel, ImproperlyConfiguredModel)


def refetch(model_instance):
    """
    Gets a fresh model instance from the database
    """
    return model_instance.__class__.objects.get(pk=model_instance.pk)


class OolTests(TestCase):
    def normal(self, model):
        x = model.objects.create(name='foo')
        x.save()
        self.assertTrue(refetch(x).name == 'foo')

        x.name = 'bar'
        x.save()

        self.assertTrue(refetch(x).name == 'bar')

    def conflict(self, model):
        x = model.objects.create(name='foo')
        x.save()

        # conflicting update
        y = refetch(x)
        y.save()

        with self.assertRaises(ConcurrentUpdate):
            x.save()
        self.assertEqual(refetch(x).name, 'foo')

    def test_simple(self):
        self.normal(SimpleModel)
        self.conflict(SimpleModel)

    def test_proxy(self):
        self.normal(ProxyModel)
        self.conflict(ProxyModel)

    def test_inheritance(self):
        self.normal(InheritedModel)
        self.conflict(InheritedModel)

    def test_unversioned_parent(self):
        self.normal(InheritedVersionedModel)
        self.conflict(InheritedVersionedModel)

    def test_update_fields_bypasses_checking(self):
        x = SimpleModel.objects.create(name='foo')
        x.save()

        y = refetch(x)
        y.name = 'bar'
        # bypass versioning by only updating a single field
        y.save(update_fields=['name'])

        x.save()
        self.assertEqual(refetch(x).name, 'foo')

    def test_get_version_field(self):
        self.assertEqual(
            SimpleModel._meta.get_field_by_name('version')[0],
            SimpleModel().get_version_field()
        )

        with self.assertRaises(ImproperlyConfigured):
            ImproperlyConfiguredModel().get_version_field()
