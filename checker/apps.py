from os import supports_dir_fd
from django.apps import AppConfig


class CheckerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'checker'
