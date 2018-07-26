from django.conf.urls import url

from django.contrib import admin

from . import views

urlpatterns = [
    url(r'^form/(?P<pk>.+)/$', views.form),
    url(r'^admin/', admin.site.urls),
]
