from django.db import models
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.contrib.admin.widgets import AdminIntegerFieldWidget


class ConcurrentUpdate(Exception):
    """
    Raised when a model can not be saved due to a concurrent update.
    """


class ReadonlyInput(forms.TextInput):
    """
    A HiddenInput would be perfect for version fields, but hidden
    inputs leave ugly empty rows in the admin. The version must
    be submitted, of course, to be checked, so we can't just use
    ModelAdmin.readonly_fields.

    Pending Django ticket #11277, this displays the version in an
    uneditable input so there's no empty row in the admin table.

    https://code.djangoproject.com/ticket/11277
    """
    def __init__(self, *args, **kwargs):
        super(ReadonlyInput, self).__init__(*args, **kwargs)
        # just readonly, because disabled won't submit the value
        self.attrs['readonly'] = 'readonly'


class VersionField(models.PositiveIntegerField):
    """
    An integer field to track versions. Every time the model is saved,
    it is incremented by one.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', 0)
        super(VersionField, self).__init__(*args, **kwargs)

    def pre_save(self, instance, add):
        new_value = getattr(instance, self.attname) + 1
        setattr(instance, self.attname, new_value)
        return new_value

    def formfield(self, **kwargs):
        widget = kwargs.get('widget')
        if widget:
            if issubclass(widget, AdminIntegerFieldWidget):
                widget = ReadonlyInput()
        else:
            widget = forms.HiddenInput
        kwargs['widget'] = widget
        return super(VersionField, self).formfield(**kwargs)


class VersionedMixin(object):
    """
    Model mixin implementing version checking during saving.
    When a concurrent update is detected, saving is aborted and
    ConcurrentUpdate will be raised.
    """

    def _do_update(self, base_qs, using, pk_val, values):
        version_field = self.get_version_field()

        # Don't check version if the version isn't being updated. This
        # also helps with model inheritance, so saves for models in the
        # hierarchy that don't have version fields don't get checked.
        if version_field not in [i[0] for i in values]:
            return super(VersionedMixin, self)._do_update(
                base_qs, using, pk_val, values)

        # pre_save has already been run, so compensate by subtracting 1
        old_version = version_field.value_from_object(self) - 1

        filter_kwargs = {
            'pk': pk_val,
            version_field.attname: old_version,
        }

        nrows = base_qs.filter(**filter_kwargs)._update(values)
        if nrows < 1:
            raise ConcurrentUpdate
        else:
            return True

    def get_version_field(self):
        for field in self._meta.fields:
            if isinstance(field, VersionField):
                return field
        raise ImproperlyConfigured(
            'VersionedMixin models must have a VersionField')
