from django.db import models

from ool import VersionField, VersionedMixin


class SimpleModel(VersionedMixin, models.Model):
    version = VersionField()
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class ProxyModel(SimpleModel):
    class Meta:
        proxy = True


class InheritedModel(SimpleModel):
    color = models.CharField(max_length=100)


class NotVersionedModel(models.Model):
    name = models.CharField(max_length=100)


class InheritedVersionedModel(VersionedMixin, NotVersionedModel):
    version = VersionField()
    color = models.CharField(max_length=100)


class ImproperlyConfiguredModel(VersionedMixin, models.Model):
    pass


class CounterModel(VersionedMixin, models.Model):
    version = VersionField()
    count = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return unicode(self.count)


class AbstractModel(VersionedMixin, models.Model):
    version = VersionField()

    class Meta:
        abstract = True


class ConcreteModel(AbstractModel):
    name = models.CharField(max_length=100)
