from django.contrib import admin

from .models import SimpleModel

admin.site.register(SimpleModel, admin.ModelAdmin)
