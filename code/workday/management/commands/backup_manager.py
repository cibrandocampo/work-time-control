import os
import time
import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backup manager'

    def handle(self, *args, **kwargs):
        max_versions = settings.BACKUP_MAX_VERSIONS
        if not os.path.exists(settings.BACKUP_PATH):
            os.makedirs(settings.BACKUP_PATH)

        while True:
            backup_start_date = timezone.now()
            for old_backup in sorted(Path(settings.BACKUP_PATH).iterdir(), key=os.path.getmtime)[:-max_versions]:
                os.remove(old_backup)

            path_dumpdata_file = settings.BACKUP_PATH + timezone.now().strftime('%d_%b_%Y-%H_%M_%S') + '_wtc_backup.xml'
            os.popen('python manage.py dumpdata --indent 4 --natural-primary'
                     ' --natural-foreign --exclude sessions.session --format xml > ' + path_dumpdata_file)

            next_loop_date = backup_start_date + datetime.timedelta(hours=settings.BACKUP_INTERVAL)
            interval_to_next_loop = int((next_loop_date - timezone.now()).total_seconds())
            seconds_to_next_loop = interval_to_next_loop if interval_to_next_loop > 1 else 1
            time.sleep(seconds_to_next_loop)
