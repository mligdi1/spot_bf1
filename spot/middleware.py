import logging
from django.conf import settings
from django.urls import resolve
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import Spot, SpotSchedule


class AdminRestrictionMiddleware:
    """Bloque automatiquement les fonctionnalités réservées aux clients pour les comptes admin.

    - Vérifie le statut admin à chaque interaction
    - Blocage préventif des actions non autorisées
    - Feedback utilisateur immédiat via messages
    - Journalisation complète des tentatives d'accès
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('bf1tv')
        # Vues (names) à bloquer pour les administrateurs
        self.blocked_views = {
            'campaign_create',
            'campaign_spot_create',
            'contact_advisor',
            'advisory_wizard',
            'guides_list',
            'guide_detail',
            'inspiration',
            'pricing_overview',
            'correspondence_new',
            'cost_simulator',
        }

    def __call__(self, request):
        user = getattr(request, 'user', None)
        try:
            match = resolve(request.path_info)
            view_name = match.view_name or ''
        except Exception:
            view_name = ''

        if getattr(user, 'is_authenticated', False) and hasattr(user, 'is_admin') and user.is_admin():
            if view_name in self.blocked_views:
                try:
                    self.logger.info(
                        'ADMIN_BLOCK | user=%s username=%s path=%s view=%s method=%s at=%s',
                        getattr(user, 'id', None), getattr(user, 'username', ''), request.path, view_name, request.method,
                        timezone.now().isoformat(timespec='seconds')
                    )
                except Exception:
                    pass
                try:
                    messages.error(request, "Cette fonctionnalité est réservée aux clients.")
                except Exception:
                    pass
                return redirect('dashboard')

        if getattr(user, 'is_authenticated', False) and hasattr(user, 'is_editorial_manager') and user.is_editorial_manager():
            media_prefix = getattr(settings, 'MEDIA_URL', '/media/') or '/media/'
            static_prefix = getattr(settings, 'STATIC_URL', '/static/') or '/static/'
            if request.path_info.startswith(media_prefix) or request.path_info.startswith(static_prefix):
                return self.get_response(request)
            allowed = False
            if view_name:
                if view_name.startswith('editorial_') or view_name.startswith('assignment_'):
                    allowed = True
                elif view_name in {'sms_inbound', 'logout', 'login', 'django.views.static.serve'}:
                    allowed = True
            if view_name and not allowed:
                try:
                    self.logger.info(
                        'EDITORIAL_BLOCK | user=%s username=%s path=%s view=%s method=%s at=%s',
                        getattr(user, 'id', None), getattr(user, 'username', ''), request.path, view_name, request.method,
                        timezone.now().isoformat(timespec='seconds')
                    )
                except Exception:
                    pass
                try:
                    messages.error(request, "Accès réservé à l’interface Rédaction.")
                except Exception:
                    pass
                return redirect('editorial_dashboard')

        return self.get_response(request)


class DiffusionStatusValidationMiddleware:
    """Vérifie systématiquement le statut des spots avant toute action de diffusion.

    - Bloque les ajouts/mises à jour de diffusion pour spots non validés
    - Cible les vues sensibles: marquage diffusé et déplacement de planning
    - Retourne une erreur claire (JSON ou redirection avec message)
    """

    # Spots autorisés pour les opérations de planning: approuvés, programmés, ou déjà diffusés
    # (les garde-fous spécifiques des vues bloquent les cas non autorisés: today/creneau déjà diffusé)
    ALLOWED_STATUSES = {'approved', 'scheduled', 'broadcasted'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ne viser que les requêtes POST
        if request.method == 'POST':
            try:
                match = resolve(request.path_info)
                view_name = match.view_name or ''
            except Exception:
                view_name = ''

            # Marquer un spot comme diffusé
            if view_name == 'diffusion_mark_broadcasted':
                spot_id = None
                try:
                    spot_id = match.kwargs.get('spot_id')
                except Exception:
                    pass
                if spot_id:
                    try:
                        spot = Spot.objects.only('id', 'status').get(id=spot_id)
                        if spot.status not in self.ALLOWED_STATUSES:
                            try:
                                messages.error(request, "Action refusée: le spot n'est pas validé.")
                            except Exception:
                                pass
                            return redirect('diffusion_spots')
                    except Spot.DoesNotExist:
                        try:
                            messages.error(request, "Spot introuvable.")
                        except Exception:
                            pass
                        return redirect('diffusion_spots')

            # Déplacer un créneau de planning
            if view_name == 'diffusion_planning_move':
                sched_id = request.POST.get('schedule_id')
                if sched_id:
                    try:
                        sched = SpotSchedule.objects.select_related('spot').only('id', 'spot__status').get(id=sched_id)
                        if getattr(sched.spot, 'status', None) not in self.ALLOWED_STATUSES:
                            return JsonResponse({'ok': False, 'error': 'spot_not_validated'}, status=403)
                    except SpotSchedule.DoesNotExist:
                        return JsonResponse({'ok': False, 'error': 'schedule_not_found'}, status=404)

            # Supprimer un créneau de planning
            if view_name == 'diffusion_planning_delete':
                sched_id = request.POST.get('schedule_id')
                if sched_id:
                    try:
                        sched = SpotSchedule.objects.select_related('spot').only('id', 'spot__status').get(id=sched_id)
                        if getattr(sched.spot, 'status', None) not in self.ALLOWED_STATUSES:
                            return JsonResponse({'ok': False, 'error': 'spot_not_validated'}, status=403)
                    except SpotSchedule.DoesNotExist:
                        return JsonResponse({'ok': False, 'error': 'schedule_not_found'}, status=404)

        return self.get_response(request)
