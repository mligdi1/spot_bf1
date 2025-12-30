from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q

from spot.models import SpotSchedule, Notification, Spot


class Command(BaseCommand):
    help = "Envoie des notifications aux diffuseurs: 10 minutes avant diffusion et retards"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Ne pas créer, juste afficher')
        parser.add_argument('--window-min', type=int, default=9, help='Fenêtre min (minutes) avant diffusion')
        parser.add_argument('--window-max', type=int, default=11, help='Fenêtre max (minutes) avant diffusion')

    def handle(self, *args, **options):
        now = timezone.now()
        window_min = options['window_min']
        window_max = options['window_max']
        upcoming_from = now + timezone.timedelta(minutes=window_min)
        upcoming_to = now + timezone.timedelta(minutes=window_max)

        # Candidats: aujourd'hui et (potentiellement) demain si on passe minuit
        candidate_dates = {timezone.localdate()}
        if upcoming_to.date() != now.date():
            candidate_dates.add(upcoming_to.date())

        # Tous les diffuseurs
        User = get_user_model()
        diffusers = list(User.objects.filter(Q(role='diffuser') | Q(groups__name__icontains='diffuser')).distinct())

        # Upcoming (10 minutes avant)
        upcoming_qs = SpotSchedule.objects.select_related('spot', 'time_slot').filter(
            broadcast_date__in=list(candidate_dates),
            is_broadcasted=False,
            spot__status__in=['approved', 'scheduled']
        )

        upcoming_count = 0
        for sched in upcoming_qs:
            sched_dt = timezone.make_aware(timezone.datetime.combine(sched.broadcast_date, sched.broadcast_time))
            if sched_dt >= upcoming_from and sched_dt <= upcoming_to:
                for user in diffusers:
                    # Anti-doublon basique: éviter répétition < 30 min sur même spot & horaire
                    dup = Notification.objects.filter(
                        user=user,
                        related_spot=sched.spot,
                        title__startswith='Diffusion dans 10 min',
                        created_at__gte=now - timezone.timedelta(minutes=30)
                    ).exists()
                    if dup:
                        continue
                    if not options['dry_run']:
                        Notification.objects.create(
                            user=user,
                            title=f"Diffusion dans 10 min: {sched.spot.title}",
                            message=f"Programmation à {sched.broadcast_time.strftime('%H:%M')} le {sched.broadcast_date.strftime('%d/%m/%Y')} (créneau: {getattr(sched.time_slot, 'name', '')}).",
                            type='warning',
                            related_spot=sched.spot,
                            related_campaign=sched.spot.campaign,
                        )
                    upcoming_count += 1

        # Retards: horaire dépassé et non diffusé
        late_qs = SpotSchedule.objects.select_related('spot', 'time_slot').filter(
            broadcast_date__lte=now.date(),
            is_broadcasted=False,
            spot__status__in=['approved', 'scheduled']
        )
        late_count = 0
        for sched in late_qs:
            sched_dt = timezone.make_aware(timezone.datetime.combine(sched.broadcast_date, sched.broadcast_time))
            if sched_dt < now:
                for user in diffusers:
                    dup = Notification.objects.filter(
                        user=user,
                        related_spot=sched.spot,
                        title__startswith='Spot en retard',
                        created_at__gte=now - timezone.timedelta(minutes=30)
                    ).exists()
                    if dup:
                        continue
                    if not options['dry_run']:
                        Notification.objects.create(
                            user=user,
                            title=f"Spot en retard: {sched.spot.title}",
                            message=f"Programmation dépassée à {sched.broadcast_time.strftime('%H:%M')} le {sched.broadcast_date.strftime('%d/%m/%Y')}. Consultez la liste des retards.",
                            type='error',
                            related_spot=sched.spot,
                            related_campaign=sched.spot.campaign,
                        )
                    late_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Notifications envoyées — upcoming={upcoming_count}, late={late_count}"
        ))