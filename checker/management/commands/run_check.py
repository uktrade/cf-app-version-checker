from django.core.management.base import BaseCommand

from checker.check import run_check

import logging

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger = logging.getLogger(__name__)
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
        run_check(logger)
