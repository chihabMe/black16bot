from django.core.management.base import BaseCommand

from broadcasts.services import recover_stuck_broadcasts


class Command(BaseCommand):
    help = "Recover broadcasts stuck in SENDING state"

    def handle(self, *args, **options):
        count = recover_stuck_broadcasts()
        if count:
            self.stdout.write(self.style.SUCCESS(f"Recovered {count} stuck broadcast(s)"))
        else:
            self.stdout.write("No stuck broadcasts found")
