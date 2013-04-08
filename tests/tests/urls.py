from django.conf.urls import patterns, url, include

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^form/(?P<pk>.+)/$', 'tests.views.form'),
    url(r'^admin/', include(admin.site.urls)),
)
