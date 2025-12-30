from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Traite les relances SMS des assignations (fallback offline-friendly)"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Ne pas envoyer, juste compter')
        parser.add_argument('--limit', type=int, default=100, help='Nombre max de campagnes à traiter')

    def handle(self, *args, **options):
        now = timezone.now()
        limit = int(options.get('limit') or 100)
        if options.get('dry_run'):
            from spot.models import AssignmentNotificationCampaign
            qs = AssignmentNotificationCampaign.objects.filter(
                status='active',
                confirmed_at__isnull=True,
                next_attempt_at__isnull=False,
                next_attempt_at__lte=now,
            ).count()
            self.stdout.write(self.style.SUCCESS(f"Due campaigns={qs}"))
            return

        from spot.utils import process_due_assignment_notification_campaigns
        processed = process_due_assignment_notification_campaigns(now=now, limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Processed={processed}"))
