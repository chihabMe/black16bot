from django.core.management.base import BaseCommand

from payments.services import expire_pending_payment_requests


class Command(BaseCommand):
    help = "Expire pending payment requests whose expiry time has passed."

    def handle(self, *args, **options):
        count = expire_pending_payment_requests()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} pending payment request(s)."))
