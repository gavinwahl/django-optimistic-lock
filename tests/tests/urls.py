from django.conf.urls import url, include

from django.contrib import admin
admin.autodiscover()

import tests.views

urlpatterns = [
    url(r'^form/(?P<pk>.+)/$', tests.views.form),
    url(r'^admin/', include(admin.site.urls)),
]
