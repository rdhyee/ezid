import os.path

import django.core.management

# The following must precede any EZID module imports:
exec(compile(open(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "tools",
        "offline.py",
    ), "rb"
).read(), os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "tools",
        "offline.py",
    ), 'exec'))

import stats


class Command(django.core.management.BaseCommand):
    help = "Compute identifier statistics"

    def handle(self, *args, **options):
        stats.recomputeStatistics()
