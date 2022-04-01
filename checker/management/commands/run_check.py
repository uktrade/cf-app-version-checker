from django.core.management.base import BaseCommand

from checker.check import run_check


class Command(BaseCommand):
    def handle(self, *args, **options):
        run_check()
