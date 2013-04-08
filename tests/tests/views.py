from django import forms
from django.views.generic import UpdateView

from .models import SimpleModel


class SimpleForm(forms.ModelForm):
    class Meta:
        model = SimpleModel


form = UpdateView.as_view(
    form_class=SimpleForm,
    model=SimpleModel,
    template_name='form.html',
    success_url='/form/%(id)s/',
)
