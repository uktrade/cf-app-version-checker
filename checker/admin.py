from django.contrib import admin

from .models import PipelineApp, PipelineEnv

admin.site.register(PipelineApp)
admin.site.register(PipelineEnv)
