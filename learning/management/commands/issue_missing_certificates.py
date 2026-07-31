from django.core.management.base import BaseCommand

from learning.models import Enrolment
from learning.services import issue_certificate


class Command(BaseCommand):
    help = 'Issue certificates for completed enrolments that do not yet have certificates.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show eligible enrolments without creating certificates.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        enrolments = Enrolment.objects.select_related(
            'student',
            'course',
        ).filter(
            status=Enrolment.Status.COMPLETED,
            certificate__isnull=True,
        )

        issued = 0
        skipped = 0

        for enrolment in enrolments:
            if dry_run:
                self.stdout.write(
                    f'Eligible: enrolment #{enrolment.pk} - {enrolment.student} / {enrolment.course}'
                )
                skipped += 1
                continue

            try:
                certificate = issue_certificate(enrolment)
            except Exception as exc:
                skipped += 1
                self.stderr.write(
                    f'Skipped enrolment #{enrolment.pk}: {exc}'
                )
            else:
                issued += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Issued {certificate.certificate_number}'
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Dry run complete. {skipped} completed enrolment(s) eligible.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Certificate issuance complete. Issued: {issued}. Skipped: {skipped}.'
            )
        )
