from django.shortcuts import render
from django.db.models import Max
from django.core.paginator import Paginator
from .models import PipelineApp, PipelineEnv

def home(request):
    last_scan_time = PipelineApp.objects.aggregate(Max('scan_start_time'))["scan_start_time__max"]
    pipeline_envs = PipelineEnv.objects.filter(pipeline_app_fk__scan_start_time=last_scan_time)
    paginator = Paginator(pipeline_envs, 100)
    page = request.GET.get('page', 1)
    return render(request, 'home.html', {
        'last_scan_time' : last_scan_time,
        'pipeline_envs' : paginator.page(page),
        }
    )
