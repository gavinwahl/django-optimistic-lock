from django import forms

from .models import SimpleModel

class SimpleForm(forms.ModelForm):
    class Meta:
        model = SimpleModel
        fields = ['name', 'version']
