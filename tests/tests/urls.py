from django.conf.urls import url, include

from django.contrib import admin
admin.autodiscover()

from . import views

urlpatterns = [
    url(r'^form/(?P<pk>.+)/$', views.form),
    url(r'^admin/', include(admin.site.urls)),
]
