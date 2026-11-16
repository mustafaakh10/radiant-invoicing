import json

from django.core.management.base import BaseCommand, CommandError

from billing.views import import_backup


class Command(BaseCommand):
    help = "Load a Radiant Billing backup (.json from this site, the Android app or the claude.ai version). Replaces all data."

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--keep", action="store_true", help="Merge into existing data instead of replacing it")

    def handle(self, file, keep=False, **kw):
        try:
            data = json.load(open(file, encoding="utf-8"))
            res = import_backup(data, replace=not keep)
        except (OSError, ValueError, KeyError) as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(f"Imported {res['records']} records and {res['photos']} photos."))
