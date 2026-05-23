from django.core.management.base import BaseCommand

from payments.verification import verify_pending_payments


class Command(BaseCommand):
    help = "Verify pending payment requests that include transaction proof."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        result = verify_pending_payments(limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {result.checked}; approved {result.approved}; failed {result.failed}."
            )
        )
        for error in result.errors:
            self.stdout.write(self.style.WARNING(error))
