from django.views.generic import UpdateView

from .models import SimpleModel
from .forms import SimpleForm


form = UpdateView.as_view(
    form_class=SimpleForm,
    model=SimpleModel,
    template_name='form.html',
    success_url='/form/%(id)s/',
)
