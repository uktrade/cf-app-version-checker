from django.shortcuts import render
from django.db.models import Max
from .models import PipelineApp, PipelineEnv

def home(request):
    last_scan_time = PipelineApp.objects.aggregate(Max('scan_start_time'))["scan_start_time__max"]
    pipeline_envs = PipelineEnv.objects.filter(config_id_fk__scan_start_time=last_scan_time)
    return render(request, 'home.html', {
        'last_scan_time' : last_scan_time,
        'pipeline_envs' : pipeline_envs,
        }
    )
