from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib import messages
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils.timezone import timedelta as tz_timedelta
import csv
import io
import os
import zipfile
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
except Exception:
    SimpleDocTemplate = None

from .models import Spot, SpotSchedule, Campaign, Notification, CampaignHistory, TimeSlot, CorrespondenceThread, CorrespondenceMessage
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# Parsing tolérant pour accepter un maximum d’entrées utilisateur
def _parse_lenient_date(s):
    s = (s or '').strip()
    if not s:
        return None
    # Formats courants
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    # Forme compacte YYYYMMDD
    digits = ''.join(ch for ch in s if ch.isdigit())
    if len(digits) == 8:
        try:
            y = int(digits[0:4])
            m = int(digits[4:6])
            d = int(digits[6:8])
            return datetime(year=y, month=m, day=d).date()
        except Exception:
            pass
    # Échec: fallback à la date du jour pour ne pas bloquer
    try:
        return timezone.localdate()
    except Exception:
        return None


def _parse_lenient_time(s):
    s = (s or '').strip().lower()
    if not s:
        return None
    # Normaliser séparateur 'h' en ':' et enlever espaces
    s = s.replace('h', ':').replace(' ', '')
    # Cas uniquement chiffres: H, HH, HMM, HHMM
    if s.isdigit():
        if len(s) == 1:
            s = f"0{s}:00"
        elif len(s) == 2:
            s = f"{s}:00"
        elif len(s) == 3:
            s = f"{s[0]}:{s[1:3]}"
        elif len(s) == 4:
            s = f"{s[0:2]}:{s[2:4]}"
    # Essais de formats
    for fmt in ['%H:%M', '%H:%M:%S']:
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            pass
    # Fallback à 00:00 si tout échoue (ne pas bloquer)
    try:
        return datetime.strptime('00:00', '%H:%M').time()
    except Exception:
        return None


def _ensure_active_timeslot(selected_slot=None, candidate_time=None):
    """Retourne un TimeSlot actif. Crée un créneau par défaut si aucun n'existe.
    - Si selected_slot est fourni, le retourne.
    - Sinon, tente de trouver un TimeSlot actif contenant candidate_time.
    - À défaut, retourne le premier TimeSlot actif.
    - Si aucun TimeSlot n'existe, crée un créneau par défaut couvrant la journée.
    """
    if selected_slot:
        return selected_slot
    qs = TimeSlot.objects.filter(is_active=True)
    if candidate_time:
        slot = qs.filter(start_time__lte=candidate_time, end_time__gt=candidate_time).order_by('start_time').first()
        if slot:
            return slot
    # Premier actif sinon
    slot = qs.order_by('start_time').first()
    if slot:
        return slot
    # Aucun créneau: créer un par défaut
    default_start = datetime.strptime('00:00', '%H:%M').time()
    default_end = datetime.strptime('23:59', '%H:%M').time()
    return TimeSlot.objects.create(
        name='Général',
        start_time=default_start,
        end_time=default_end,
        price_multiplier=Decimal('1.00'),
        description="Créneau par défaut (toute la journée)",
        is_active=True,
        is_prime=False
    )


def _planning_item_payload(sched: SpotSchedule):
    try:
        return {
            'id': str(sched.id),
            'date_iso': sched.broadcast_date.isoformat(),
            'time_iso': sched.broadcast_time.strftime('%H:%M:%S'),
            'date_str': sched.broadcast_date.strftime('%d/%m/%Y'),
            'time_str': sched.broadcast_time.strftime('%H:%M'),
            'title': getattr(sched.spot, 'title', ''),
            'client': getattr(getattr(sched.spot, 'campaign', None), 'client', None) and getattr(sched.spot.campaign.client, 'username', '') or '',
            'media_type': getattr(sched.spot, 'media_type', ''),
            'duration_seconds': getattr(sched.spot, 'duration_seconds', None),
            'spot_id': str(getattr(sched.spot, 'id', '')),
            'has_media': bool(getattr(sched.spot, 'video_file', None) or getattr(sched.spot, 'image_file', None)),
            'is_broadcasted': bool(getattr(sched, 'is_broadcasted', False)),
        }
    except Exception:
        return {'id': str(getattr(sched, 'id', '')), 'date_iso': '', 'time_iso': '', 'title': getattr(getattr(sched, 'spot', None), 'title', '')}


def _emit_planning_upsert(sched: SpotSchedule):
    try:
        layer = get_channel_layer()
        if not layer:
            return
        payload = _planning_item_payload(sched)
        async_to_sync(layer.group_send)('planning_updates', {
            'type': 'planning_update',
            'action': 'upsert',
            'item': payload,
        })
    except Exception:
        # silencieux pour ne pas bloquer la réponse HTTP
        pass


def _base_context(user):
    """Contexte de base pour toutes les pages Diffusion"""
    return {
        'user': user,
    }


@login_required
def home(request):
    """Page d'accueil Diffusion avec KPI clés"""
    ctx = _base_context(request.user)
    today = timezone.localdate()
    # KPI
    spots_today_count = SpotSchedule.objects.filter(broadcast_date=today).count()
    late_spots_count = SpotSchedule.objects.filter(broadcast_date__lt=today, is_broadcasted=False).count()
    start_week = today - timezone.timedelta(days=today.weekday())
    week_days = [start_week + timezone.timedelta(days=i) for i in range(7)]
    week_counts = {
        d.strftime('%a %d/%m'): SpotSchedule.objects.filter(broadcast_date=d).count()
        for d in week_days
    }

    # Listes pour synthèse
    spots_today_list = SpotSchedule.objects.select_related('spot', 'spot__campaign__client')\
        .filter(broadcast_date=today).order_by('broadcast_time')[:20]
    late_spots_list = SpotSchedule.objects.select_related('spot', 'spot__campaign__client')\
        .filter(broadcast_date__lt=today, is_broadcasted=False).order_by('-broadcast_date', 'broadcast_time')[:20]

    ctx.update({
        'kpi_spots_today': spots_today_count,
        'kpi_late_spots': late_spots_count,
        'kpi_week_counts': week_counts,
        'spots_today_list': spots_today_list,
        'late_spots_list': late_spots_list,
    })
    return render(request, 'spot/diffusion/home.html', ctx)


@login_required
def profile(request):
    """Profil diffuseur"""
    user = request.user
    # Edition du profil via POST
    if request.method == 'POST':
        # Récupération et nettoyage des champs
        first_name = (request.POST.get('first_name') or '').strip() or user.first_name
        last_name = (request.POST.get('last_name') or '').strip() or user.last_name
        email = (request.POST.get('email') or '').strip() or user.email
        phone = (request.POST.get('phone') or '').strip() or getattr(user, 'phone', '')
        company = (request.POST.get('company') or '').strip() or getattr(user, 'company', '')
        address = (request.POST.get('address') or '').strip() or getattr(user, 'address', '')

        password = (request.POST.get('password') or '').strip()

        # Validation légère
        errors = []
        if not email:
            errors.append("L’adresse email est requise.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Le format de l’adresse email est invalide.")
            else:
                UserModel = get_user_model()
                if UserModel.objects.filter(email=email).exclude(pk=user.pk).exists():
                    errors.append("Cette adresse email est déjà utilisée par un autre compte.")

        if password and len(password) < 8:
            errors.append("Le mot de passe doit comporter au moins 8 caractères.")

        if errors:
            for e in errors:
                messages.error(request, e)
            # En cas d’erreur, ne pas mettre à jour. Afficher la page avec messages.
            ctx = _base_context(user)
            today = timezone.localdate()
            spots_today = SpotSchedule.objects.filter(broadcast_date=today).count()
            late_spots = SpotSchedule.objects.filter(broadcast_date__lt=today, is_broadcasted=False).count()
            start_week = today - timezone.timedelta(days=today.weekday())
            week_days = [start_week + timezone.timedelta(days=i) for i in range(7)]
            week_counts = {
                d.strftime('%a %d/%m'): SpotSchedule.objects.filter(broadcast_date=d).count()
                for d in week_days
            }
            # Activités récentes: uniquement les spots non planifiés (sans schedule)
            activities_qs = Spot.objects.filter(schedules__isnull=True).order_by('-created_at')[:10]
            ctx.update({
                'kpi_spots_today': spots_today,
                'kpi_late_spots': late_spots,
                'kpi_week_counts': week_counts,
                'activities': activities_qs,
            })
            return render(request, 'spot/diffusion/profile.html', ctx)

        # Mise à jour si validation ok
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        if hasattr(user, 'phone'):
            user.phone = phone
        if hasattr(user, 'company'):
            user.company = company
        if hasattr(user, 'address'):
            user.address = address

        if password:
            user.set_password(password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Votre mot de passe a été mis à jour et vous restez connecté.")
        else:
            user.save()
            messages.success(request, "Votre profil a été mis à jour avec succès !")

        return redirect('diffusion_profile')

    ctx = _base_context(user)
    # KPI basiques
    today = timezone.localdate()
    spots_today = SpotSchedule.objects.filter(broadcast_date=today).count()
    late_spots = SpotSchedule.objects.filter(broadcast_date__lt=today, is_broadcasted=False).count()
    start_week = today - timezone.timedelta(days=today.weekday())
    week_days = [start_week + timezone.timedelta(days=i) for i in range(7)]
    week_counts = {
        d.strftime('%a %d/%m'): SpotSchedule.objects.filter(broadcast_date=d).count()
        for d in week_days
    }
    # Activités récentes: uniquement les spots non planifiés (sans schedule)
    activities_qs = Spot.objects.filter(schedules__isnull=True).order_by('-created_at')[:10]
    ctx.update({
        'kpi_spots_today': spots_today,
        'kpi_late_spots': late_spots,
        'kpi_week_counts': week_counts,
        'activities': activities_qs,
    })
    return render(request, 'spot/diffusion/profile.html', ctx)


    


@login_required
def spots_list(request):
    """Liste des spots à diffuser avec filtres et actions"""
    # N'inclure que les spots validés côté diffuseur
    qs = Spot.objects.select_related('campaign__client').filter(status='approved')
    # Filtres
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    media_type = request.GET.get('type')
    if media_type:
        qs = qs.filter(media_type=media_type)
    client = request.GET.get('client')
    if client:
        qs = qs.filter(campaign__client__username__icontains=client)
    # Filtre de durée (15/30/60 sec)
    duration = request.GET.get('duration')
    if duration in {'15','30','60'}:
        try:
            qs = qs.filter(duration_seconds=int(duration))
        except ValueError:
            pass
    # Filtre par date (aujourd'hui/demain/semaine/mois ou personnalisé)
    date_range = (request.GET.get('date') or '').lower()
    today = timezone.localdate()
    if date_range == 'today':
        qs = qs.filter(schedules__broadcast_date=today)
    elif date_range == 'tomorrow':
        qs = qs.filter(schedules__broadcast_date=today + timezone.timedelta(days=1))
    elif date_range == 'week':
        start_week = today - timezone.timedelta(days=today.weekday())
        end_week = start_week + timezone.timedelta(days=7)
        qs = qs.filter(schedules__broadcast_date__gte=start_week, schedules__broadcast_date__lt=end_week)
    elif date_range == 'month':
        start_month = today.replace(day=1)
        if start_month.month == 12:
            next_month = start_month.replace(year=start_month.year+1, month=1)
        else:
            next_month = start_month.replace(month=start_month.month+1)
        qs = qs.filter(schedules__broadcast_date__gte=start_month, schedules__broadcast_date__lt=next_month)
    elif date_range == 'custom':
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        try:
            if date_from:
                df = timezone.datetime.fromisoformat(date_from).date()
                qs = qs.filter(schedules__broadcast_date__gte=df)
            if date_to:
                dt = timezone.datetime.fromisoformat(date_to).date()
                qs = qs.filter(schedules__broadcast_date__lte=dt)
        except Exception:
            pass

    qs = qs.distinct()
    # Tri
    sort = (request.GET.get('sort') or '').strip()
    if sort == 'campaign_start_desc':
        qs = qs.order_by('-campaign__start_date', '-campaign__end_date', '-created_at')
    elif sort == 'campaign_start_asc':
        qs = qs.order_by('campaign__start_date', 'campaign__end_date', 'created_at')
    elif sort == 'next_broadcast_desc':
        qs = qs.order_by('-schedules__broadcast_date', '-schedules__broadcast_time', '-created_at')
    elif sort == 'next_broadcast_asc':
        qs = qs.order_by('schedules__broadcast_date', 'schedules__broadcast_time', 'created_at')
    elif sort == 'client_asc':
        qs = qs.order_by('campaign__client__username', 'created_at')
    elif sort == 'client_desc':
        qs = qs.order_by('-campaign__client__username', '-created_at')
    elif sort == 'date_desc':
        qs = qs.order_by('-created_at')
    elif sort == 'date_asc':
        qs = qs.order_by('created_at')
    else:
        # Par défaut: prioriser les campagnes qui débutent le plus tôt
        qs = qs.order_by('campaign__start_date', 'campaign__end_date', 'created_at')

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    ctx = _base_context(request.user)
    ctx.update({
        'page_obj': page_obj,
        'status_choices': Spot.STATUS_CHOICES,
        'now': timezone.now(),
    })
    return render(request, 'spot/diffusion/spots.html', ctx)


def _filter_broadcasted_schedules(request):
    """Construit le queryset des programmations diffusées avec filtres communs."""
    qs = SpotSchedule.objects.select_related('spot__campaign', 'time_slot').filter(is_broadcasted=True)

    # Recherche plein-texte
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(spot__title__icontains=q) |
            Q(spot__campaign__title__icontains=q) |
            Q(spot__campaign__client__username__icontains=q)
        )

    # Client
    client = (request.GET.get('client') or '').strip()
    if client:
        qs = qs.filter(spot__campaign__client__username__icontains=client)

    # Canal
    channel = (request.GET.get('channel') or '').strip()
    if channel:
        qs = qs.filter(spot__campaign__channel=channel)

    # Type média
    media_type = (request.GET.get('type') or '').strip()
    if media_type in {'image', 'video'}:
        qs = qs.filter(spot__media_type=media_type)

    # Durée (min/max en secondes)
    dur_min = request.GET.get('dur_min')
    dur_max = request.GET.get('dur_max')
    try:
        if dur_min:
            qs = qs.filter(spot__duration_seconds__gte=int(dur_min))
        if dur_max:
            qs = qs.filter(spot__duration_seconds__lte=int(dur_max))
    except Exception:
        pass

    # Plage de dates
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    try:
        if date_from:
            df = timezone.datetime.fromisoformat(date_from).date()
            qs = qs.filter(broadcast_date__gte=df)
        if date_to:
            dt = timezone.datetime.fromisoformat(date_to).date()
            qs = qs.filter(broadcast_date__lte=dt)
    except Exception:
        pass

    # Tri
    sort = (request.GET.get('sort') or '').strip()
    if sort == 'date_asc':
        qs = qs.order_by('broadcast_date', 'broadcast_time')
    elif sort == 'date_desc':
        qs = qs.order_by('-broadcast_date', '-broadcast_time')
    elif sort == 'client_asc':
        qs = qs.order_by('spot__campaign__client__username', 'broadcast_date', 'broadcast_time')
    elif sort == 'client_desc':
        qs = qs.order_by('-spot__campaign__client__username', '-broadcast_date', '-broadcast_time')
    else:
        qs = qs.order_by('-broadcast_date', '-broadcast_time')

    return qs


@login_required
def spots_broadcasted_list(request):
    """Vue: liste des spots diffusés (basée sur SpotSchedule.is_broadcasted)"""
    qs = _filter_broadcasted_schedules(request)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    ctx = _base_context(request.user)
    ctx.update({
        'page_obj': page_obj,
        'channels': [('tv', 'Télévision'), ('urban', 'Écran urbain'), ('online', 'En ligne')],
        'now': timezone.now(),
    })
    return render(request, 'spot/diffusion/spots_broadcasted.html', ctx)


@login_required
def export_spots_broadcasted_pdf(request):
    """Export PDF des spots diffusés. Téléchargement immédiat d'un document professionnel.

    Contient: titre du spot, client, date/heure de diffusion, durée, canal, métadonnées.
    """
    if SimpleDocTemplate is None:
        messages.error(request, "Veuillez installer reportlab (pip install reportlab) pour exporter en PDF.")
        return redirect('diffusion_spots_broadcasted')

    qs = _filter_broadcasted_schedules(request)
    # Construire le PDF
    from io import BytesIO
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Spots diffusés")
    styles = getSampleStyleSheet()
    story = []

    # Titre
    story.append(Paragraph("<b>Liste des spots diffusés</b>", styles['Title']))
    story.append(Spacer(1, 12))

    # Sous-titre: période si fournie
    df = (request.GET.get('date_from') or '').strip()
    dt = (request.GET.get('date_to') or '').strip()
    subtitle = "Période: tout"
    if df or dt:
        subtitle = f"Période: {df or '—'} → {dt or '—'}"
    story.append(Paragraph(subtitle, styles['Normal']))
    story.append(Spacer(1, 12))

    # En-tête tableau (sans colonne Méta)
    data = [[
        'Spot', 'Client', 'Date', 'Heure', 'Durée (s)', 'Canal'
    ]]

    # Lignes
    for s in qs[:1000]:  # borne de sécurité
        spot = s.spot
        client = getattr(spot.campaign.client, 'username', '')
        date_str = s.broadcast_date.strftime('%d/%m/%Y') if s.broadcast_date else ''
        time_str = s.broadcast_time.strftime('%H:%M') if s.broadcast_time else ''
        duration = spot.duration_seconds or ''
        channel = getattr(spot.campaign, 'channel', '') or ''
        data.append([
            spot.title,
            client,
            date_str,
            time_str,
            duration,
            channel,
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightyellow]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    resp = HttpResponse(buffer.read(), content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="spots_diffuses.pdf"'
    return resp


@login_required
def clients_search_api(request):
    """Recherche prédictive de clients (username)"""
    q = (request.GET.get('q') or '').strip()
    results = []
    if q:
        clients = Campaign.objects.select_related('client').filter(client__username__icontains=q)[:8]
        for c in clients:
            if getattr(c, 'client', None):
                results.append({'username': c.client.username})
    return JsonResponse({'results': results})


@login_required
def mark_spot_broadcasted(request, spot_id):
    spot = get_object_or_404(Spot, id=spot_id)
    if request.method == 'POST':
        # Contrôle préliminaire: présence média
        file_present = bool(spot.video_file) or bool(spot.image_file)
        if not file_present:
            messages.error(request, "Impossible de confirmer: aucun fichier média associé.")
            return redirect('diffusion_spots')

        today = timezone.localdate()
        try:
            with transaction.atomic():
                # Verrous pessimistes pour éviter la double mise à jour concurrente
                spot_locked = Spot.objects.select_for_update().get(id=spot.id)
                schedules_qs = SpotSchedule.objects.select_for_update().filter(
                    spot=spot_locked, broadcast_date__lte=today, is_broadcasted=False
                )
                updated_count = schedules_qs.update(is_broadcasted=True, broadcasted_at=timezone.now())

                if updated_count > 0:
                    spot_locked.status = 'broadcasted'
                    spot_locked.save(update_fields=['status'])
                    messages.success(request, f"{updated_count} créneau(x) confirmé(s) comme diffusé(s).")
                else:
                    messages.info(request, "Aucun créneau en attente pour ce spot (déjà confirmé ou futur).")
        except Exception as e:
            import logging
            logging.getLogger('bf1tv').exception('DIFFUSION_MARK_BROADCASTED_ERROR spot=%s err=%s', str(spot_id), str(e))
            messages.error(request, "Erreur lors de la confirmation de diffusion. Réessayez ou contactez l’admin.")
    return redirect('diffusion_spots')


@login_required
def planning_confirm_broadcast(request):
    """Confirme la diffusion pour un créneau donné (jour J uniquement).

    Attendu: POST avec 'schedule_id'. Met à jour sched.is_broadcasted, sched.broadcasted_at,
    et met éventuellement le statut du spot à 'broadcasted' si tous les créneaux passés sont confirmés.
    Émet une mise à jour temps réel vers le Planning et historise l'action.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)
    sid = request.POST.get('schedule_id')
    if not sid:
        return JsonResponse({'ok': False, 'error': 'missing_params'}, status=400)
    try:
        sched = SpotSchedule.objects.select_related('spot', 'spot__campaign').get(id=int(sid) if str(sid).isdigit() else sid)
    except SpotSchedule.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)

    # Validations
    today = timezone.localdate()
    # Autoriser aussi les spots déjà "diffusés" (ex: confirmation de nouveaux créneaux)
    if getattr(sched.spot, 'status', None) not in {'approved', 'scheduled', 'broadcasted'}:
        return JsonResponse({'ok': False, 'error': 'spot_not_validated'}, status=403)
    if sched.broadcast_date != today:
        return JsonResponse({'ok': False, 'error': 'not_today'}, status=403)
    if sched.is_broadcasted:
        return JsonResponse({'ok': False, 'error': 'already_broadcasted'}, status=422)
    # Contrôle média présent
    file_present = bool(getattr(sched.spot, 'video_file', None)) or bool(getattr(sched.spot, 'image_file', None))
    if not file_present:
        return JsonResponse({'ok': False, 'error': 'no_media'}, status=422)

    try:
        with transaction.atomic():
            # Verrouiller le créneau et le spot
            locked_sched = SpotSchedule.objects.select_for_update().get(id=sched.id)
            locked_spot = Spot.objects.select_for_update().get(id=sched.spot_id)

            if locked_sched.is_broadcasted:
                return JsonResponse({'ok': False, 'error': 'already_broadcasted'}, status=422)

            locked_sched.is_broadcasted = True
            locked_sched.broadcasted_at = timezone.now()
            locked_sched.save(update_fields=['is_broadcasted', 'broadcasted_at'])

            # Mettre à jour le statut du spot si tous les créneaux jusqu'à aujourd'hui sont confirmés
            remaining = SpotSchedule.objects.filter(
                spot=locked_spot,
                broadcast_date__lte=today,
                is_broadcasted=False
            ).exists()
            if not remaining and locked_spot.status != 'broadcasted':
                locked_spot.status = 'broadcasted'
                locked_spot.save(update_fields=['status'])

            # Historique
            CampaignHistory.objects.create(
                campaign=locked_spot.campaign,
                action='broadcast_confirmed',
                description=f"Diffusion confirmée pour '{locked_spot.title}' — {locked_sched.broadcast_date} {locked_sched.broadcast_time}",
                user=request.user,
            )

    except Exception as e:
        import logging
        logging.getLogger('bf1tv').exception('PLANNING_CONFIRM_BROADCAST_ERROR sched=%s err=%s', str(sid), str(e))
        return JsonResponse({'ok': False, 'error': 'server_error'}, status=500)

    # Émettre update temps réel
    try:
        _emit_planning_upsert(locked_sched)
    except Exception:
        pass

    return JsonResponse({'ok': True, 'item': _planning_item_payload(locked_sched)})


@login_required
def planning_undo_broadcast(request):
    """Annule une confirmation de diffusion pour un créneau, dans une fenêtre courte.

    Attendu: POST avec 'schedule_id'. Autorise l'annulation si broadcasted_at < 5 minutes.
    Réinitialise sched.is_broadcasted et ajuste le statut du spot si nécessaire.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)
    sid = request.POST.get('schedule_id')
    if not sid:
        return JsonResponse({'ok': False, 'error': 'missing_params'}, status=400)
    try:
        sched = SpotSchedule.objects.select_related('spot', 'spot__campaign').get(id=int(sid) if str(sid).isdigit() else sid)
    except SpotSchedule.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)

    if not sched.is_broadcasted:
        return JsonResponse({'ok': False, 'error': 'not_broadcasted'}, status=422)

    # Fenêtre d'annulation: 5 minutes par défaut
    try:
        if not sched.broadcasted_at or (timezone.now() - sched.broadcasted_at) > tz_timedelta(minutes=5):
            return JsonResponse({'ok': False, 'error': 'undo_window_expired'}, status=403)
    except Exception:
        # Si comparaison échoue, ne pas autoriser l'annulation
        return JsonResponse({'ok': False, 'error': 'undo_window_expired'}, status=403)

    try:
        with transaction.atomic():
            locked_sched = SpotSchedule.objects.select_for_update().get(id=sched.id)
            locked_spot = Spot.objects.select_for_update().get(id=sched.spot_id)

            if not locked_sched.is_broadcasted:
                return JsonResponse({'ok': False, 'error': 'not_broadcasted'}, status=422)

            locked_sched.is_broadcasted = False
            locked_sched.broadcasted_at = None
            locked_sched.save(update_fields=['is_broadcasted', 'broadcasted_at'])

            # Ajuster le statut du spot si nécessaire
            today = timezone.localdate()
            has_unconfirmed_past = SpotSchedule.objects.filter(
                spot=locked_spot,
                broadcast_date__lte=today,
                is_broadcasted=False
            ).exists()
            if has_unconfirmed_past and locked_spot.status == 'broadcasted':
                locked_spot.status = 'scheduled'
                locked_spot.save(update_fields=['status'])

            CampaignHistory.objects.create(
                campaign=locked_spot.campaign,
                action='broadcast_undone',
                description=f"Annulation de confirmation pour '{locked_spot.title}' — {locked_sched.broadcast_date} {locked_sched.broadcast_time}",
                user=request.user,
            )
    except Exception as e:
        import logging
        logging.getLogger('bf1tv').exception('PLANNING_UNDO_BROADCAST_ERROR sched=%s err=%s', str(sid), str(e))
        return JsonResponse({'ok': False, 'error': 'server_error'}, status=500)

    try:
        _emit_planning_upsert(locked_sched)
    except Exception:
        pass

    return JsonResponse({'ok': True, 'item': _planning_item_payload(locked_sched)})


@login_required
def notify_broadcast_time(request, spot_id):
    """Fournit les détails de programmation et envoie des notifications.

    GET (AJAX): renvoie les détails de la prochaine programmation du spot.
    POST (AJAX): envoie des notifications selon les options choisies (admin/client).
    """
    spot = get_object_or_404(Spot, id=spot_id)
    today = timezone.localdate()

    # Chercher la prochaine diffusion (aujourd’hui ou après), sinon toute première existante
    next_sched = spot.schedules.filter(broadcast_date__gte=today).order_by('broadcast_date', 'broadcast_time').first() or \
                 spot.schedules.order_by('broadcast_date', 'broadcast_time').first()

    # Mode GET: renvoyer les détails pour affichage dans une modal
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if not next_sched:
            # Pas de programmation: proposer la création sans gérer les créneaux côté UI
            data = {
                'ok': True,
                'has_schedule': False,
                'spot_title': spot.title,
                'campaign_title': spot.campaign.title,
                'channel': getattr(spot.campaign, 'channel', None),
                'broadcast_date': str(today),
                'broadcast_time': '',
                'is_broadcasted': False,
                'duration_seconds': spot.duration_seconds,
            }
            return JsonResponse(data)

        # Détails étendus pour une programmation existante (affichage informatif du créneau)
        data = {
            'ok': True,
            'has_schedule': True,
            'spot_title': spot.title,
            'campaign_title': spot.campaign.title,
            'channel': getattr(spot.campaign, 'channel', None),
            'time_slot': getattr(next_sched.time_slot, 'name', None),
            'broadcast_date': str(getattr(next_sched, 'broadcast_date', '')),
            'broadcast_time': str(getattr(next_sched, 'broadcast_time', '')),
            'is_broadcasted': bool(getattr(next_sched, 'is_broadcasted', False)),
            'duration_seconds': spot.duration_seconds,
        }
        return JsonResponse(data)

    # Mode POST: envoyer notifications selon options, avec confirmation/modification des champs
    if request.method == 'POST':
        # Lecture des champs éventuels de confirmation/modification
        new_date_str = (request.POST.get('broadcast_date') or '').strip()
        new_time_str = (request.POST.get('broadcast_time') or '').strip()
        new_duration_str = (request.POST.get('duration_seconds') or '').strip()
        time_slot_id_str = (request.POST.get('time_slot_id') or '').strip()

        # Parsing tolérant: si l'utilisateur donne date/heure, on les rend valides
        new_date = _parse_lenient_date(new_date_str) if new_date_str else None
        new_time = _parse_lenient_time(new_time_str) if new_time_str else None

        # Appliquer les modifications si fournies
        selected_slot = None
        # Si un time_slot_id est fourni (anciens clients), on l'utilise; sinon on déduit du temps final
        if time_slot_id_str:
            try:
                selected_slot = TimeSlot.objects.get(id=int(time_slot_id_str))
            except (ValueError, TimeSlot.DoesNotExist):
                selected_slot = None

        if next_sched:
            # Mise à jour d'une programmation existante
            if new_date:
                next_sched.broadcast_date = new_date
            if new_time:
                next_sched.broadcast_time = new_time
            # Déduire un créneau si utile (informative), mais ne pas bloquer
            final_time = next_sched.broadcast_time or new_time
            selected_slot = _ensure_active_timeslot(selected_slot, final_time)
            fields = ['broadcast_date', 'broadcast_time']
            if selected_slot and (not next_sched.time_slot_id or next_sched.time_slot_id != selected_slot.id):
                # Conflit éventuel uniquement si on change le créneau et que même (date, heure) existe
                if (getattr(next_sched, 'broadcast_date', None) and getattr(next_sched, 'broadcast_time', None)):
                    exists_conflict = SpotSchedule.objects.filter(
                        time_slot=selected_slot,
                        broadcast_date=next_sched.broadcast_date,
                        broadcast_time=next_sched.broadcast_time
                    ).exclude(id=next_sched.id).exists()
                    if exists_conflict:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({'ok': False, 'error': 'schedule_conflict'}, status=409)
                        messages.error(request, "Conflit de programmation: un créneau existe déjà pour cette date et cette heure.")
                        return redirect('diffusion_spots')
                next_sched.time_slot = selected_slot
                fields.append('time_slot')
            next_sched.save(update_fields=fields)
        else:
            # Création d'une première programmation à la volée
            if not (new_date_str and new_time_str):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': 'missing_datetime'}, status=400)
                messages.error(request, "Renseignez la date et l'heure.")
                return redirect('diffusion_spots')
            # Si parsing non concluant, on prend des valeurs par défaut non bloquantes
            if not new_date:
                new_date = timezone.localdate()
            if not new_time:
                new_time = datetime.strptime('00:00', '%H:%M').time()
            selected_slot = _ensure_active_timeslot(selected_slot, new_time)
            # Prix par défaut; à raffiner via PricingRule si nécessaire
            price = Decimal('0')
            try:
                next_sched = SpotSchedule.objects.create(
                    spot=spot,
                    time_slot=selected_slot,
                    broadcast_date=new_date,
                    broadcast_time=new_time,
                    price=price,
                    is_broadcasted=False,
                )
            except IntegrityError:
                # Conflit d'unicité (time_slot, date, heure)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'ok': False, 'error': 'schedule_conflict'}, status=409)
                messages.error(request, "Conflit de programmation: un créneau existe déjà pour cette date et cette heure.")
                return redirect('diffusion_spots')

        if new_duration_str:
            try:
                spot.duration_seconds = int(new_duration_str)
                spot.save(update_fields=['duration_seconds'])
            except ValueError:
                # Ne pas bloquer la confirmation si la durée est invalide: ignorer la mise à jour
                pass

        # Mettre à jour le statut du spot
        spot.status = 'scheduled'
        spot.save(update_fields=['status'])

        # Émettre mise à jour pour la page Planning (déclassement automatique)
        try:
            if next_sched:
                _emit_planning_upsert(next_sched)
        except Exception:
            pass

        # Historiser l'action
        CampaignHistory.objects.create(
            campaign=spot.campaign,
            action='updated',
            description=f"Programmation confirmée: {next_sched.broadcast_date} {next_sched.broadcast_time}; durée={spot.duration_seconds or '-'}s",
            user=request.user,
        )

        # Notification et message
        when_txt = f"{next_sched.broadcast_date} {next_sched.broadcast_time}"
        notif_title = "Information sur le moment de diffusion"
        notif_msg = f"Le spot '{spot.title}' est programmé le {when_txt}."

        # Options d’envoi (par défaut: les deux)
        notify_admin = (request.POST.get('notify_admin') or 'true').lower() in ['true', '1', 'yes', 'on']
        notify_client = (request.POST.get('notify_client') or 'true').lower() in ['true', '1', 'yes', 'on']

        # Notifier le client
        if notify_client and getattr(spot.campaign, 'client', None):
            Notification.objects.create(
                user=spot.campaign.client,
                title=notif_title,
                message=notif_msg,
                type='info',
                related_campaign=spot.campaign,
                related_spot=spot,
            )

        # Notifier les administrateurs
        if notify_admin:
            UserModel = get_user_model()
            admins = UserModel.objects.filter(role='admin')
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title=notif_title,
                    message=f"[Admin] {notif_msg}",
                    type='info',
                    related_campaign=spot.campaign,
                    related_spot=spot,
                )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'when': when_txt,
                'sent_admin': notify_admin,
                'sent_client': notify_client,
                'duration_seconds': spot.duration_seconds,
                'broadcast_date': str(next_sched.broadcast_date),
                'broadcast_time': str(next_sched.broadcast_time),
            })

        messages.success(request, f"Programmation sauvegardée et notifications envoyées: {when_txt}.")
        return redirect('diffusion_spots')

    # Fallback non-AJAX GET: message + redirect
    if not next_sched:
        messages.info(request, "Aucune programmation disponible pour ce spot.")
        return redirect('diffusion_spots')
    messages.info(request, "Sélectionnez les options d’envoi.")
    return redirect('diffusion_spots')


@login_required
def report_problem(request, spot_id):
    spot = get_object_or_404(Spot, id=spot_id)
    ctx = _base_context(request.user)
    if request.method == 'POST':
        description = (request.POST.get('description') or '').strip()
        severity = (request.POST.get('severity') or '').strip().lower()

        # Validation simple côté serveur
        valid_severity = {'low', 'medium', 'high'}
        if not description or len(description) < 10 or severity not in valid_severity:
            messages.error(request, "Veuillez fournir une description (≥10 caractères) et une gravité.")
            ctx.update({'spot': spot})
            return render(request, 'spot/diffusion/report_problem.html', ctx)

        # Journaliser pour traçabilité
        import logging
        logging.getLogger('bf1tv').info(
            'DIFFUSION_REPORT | user=%s spot=%s severity=%s message=%s',
            request.user.username, str(spot.id), severity, description[:500]
        )

        # Créer un fil de correspondance et le premier message, et notifier les admins
        try:
            with transaction.atomic():
                # Priorité: "high" => urgent, sinon normal
                priority = 'urgent' if severity == 'high' else 'normal'
                thread = CorrespondenceThread.objects.create(
                    client=request.user,
                    subject=f'Problème sur le spot "{spot.title}"',
                    status='pending',
                    related_campaign=spot.campaign,
                    priority=priority,
                )
                CorrespondenceMessage.objects.create(
                    thread=thread,
                    author=request.user,
                    content=description,
                )

                # Type de notification selon gravité
                notif_type = 'error' if severity == 'high' else 'warning'
                # Notifier tous les administrateurs
                AdminUser = get_user_model()
                admins = AdminUser.objects.filter(role='admin')
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        title='Problème signalé sur un spot',
                        message=(
                            f'Severité: {severity.upper()} | Spot: "{spot.title}" | '
                            f'Détails: {description[:200]}'
                        ),
                        type=notif_type,
                        related_campaign=spot.campaign,
                        related_spot=spot,
                        related_thread=thread,
                    )

            messages.success(request, "Votre signalement a été envoyé. Nos administrateurs ont été notifiés.")
        except Exception as e:
            messages.error(request, "Une erreur est survenue lors de l’envoi du signalement. Réessayez.")
            import logging
            logging.getLogger('bf1tv').exception('DIFFUSION_REPORT_ERROR | spot=%s err=%s', str(spot.id), e)

        return redirect('diffusion_spots')

    ctx.update({'spot': spot})
    return render(request, 'spot/diffusion/report_problem.html', ctx)


@login_required
def spot_detail_diffusion(request, spot_id):
    """Détail du spot pour les diffuseurs (lecture seule) avec aperçu média."""
    spot = get_object_or_404(Spot, id=spot_id)
    # La vérification d'accès diffuseur est appliquée au niveau de l'URL via is_diffuser_required
    media_url = None
    if getattr(spot, 'video_file', None) and getattr(spot.video_file, 'url', None):
        media_url = spot.video_file.url
    elif getattr(spot, 'image_file', None) and getattr(spot.image_file, 'url', None):
        media_url = spot.image_file.url

    schedules = SpotSchedule.objects.filter(spot=spot).order_by('broadcast_date', 'broadcast_time')
    ctx = _base_context(request.user)
    ctx.update({
        'spot': spot,
        'media_url': media_url,
        'schedules': schedules,
    })
    return render(request, 'spot/diffusion/spot_detail.html', ctx)


@login_required
def notifications_diffusion(request):
    """Notifications pour le diffuseur (mise en page diffusion)"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)

    ctx = _base_context(request.user)
    ctx.update({'notifications': notifications, 'unread_count': unread_count})
    return render(request, 'spot/diffusion/notifications.html', ctx)


@login_required
def bulk_schedule_spot(request, spot_id):
    """Création de programmations multiples pour un spot (plage de dates et jours).

    Champs attendus (POST):
    - start_date (YYYY-MM-DD)
    - end_date (YYYY-MM-DD)
    - broadcast_time (HH:MM)
    - days (liste CSV parmi: mon,tue,wed,thu,fri,sat,sun) optionnel, par défaut tous les jours
    - time_slot_id (optionnel)
    """
    spot = get_object_or_404(Spot, id=spot_id)
    if request.method != 'POST':
        # Retour propre vers la page du spot si accès direct
        return redirect('diffusion_spot_detail', spot_id=spot_id)

    # Vérifier statut spot
    if spot.status not in ['approved', 'scheduled', 'broadcasted']:
        return JsonResponse({'ok': False, 'error': 'spot_not_validated'}, status=403)

    start_date_str = request.POST.get('start_date')
    end_date_str = request.POST.get('end_date') or start_date_str
    time_str = request.POST.get('broadcast_time')
    days_csv = (request.POST.get('days') or '').strip()
    time_slot_id_str = request.POST.get('time_slot_id')

    if not start_date_str or not time_str:
        return JsonResponse({'ok': False, 'error': 'missing_params'}, status=400)

    try:
        start_d = parse_date(start_date_str)
        end_d = parse_date(end_date_str)
        if not start_d or not end_d:
            raise ValueError('invalid_date')
        if end_d < start_d:
            raise ValueError('end_before_start')
        # Parse heure
        t = timezone.datetime.fromisoformat(f"1970-01-01T{time_str}:00").time() if len(time_str) == 5 else timezone.datetime.fromisoformat(f"1970-01-01T{time_str}").time()
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_datetime'}, status=400)

    # Jours de semaine autorisés
    days_map = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
    selected_days = set()
    if days_csv:
        for part in days_csv.split(','):
            key = part.strip().lower()
            if key in days_map:
                selected_days.add(days_map[key])
    else:
        selected_days = set(range(7))  # tous les jours

    # Déterminer le créneau
    selected_slot = None
    if time_slot_id_str:
        try:
            selected_slot = TimeSlot.objects.get(id=int(time_slot_id_str))
        except (ValueError, TimeSlot.DoesNotExist):
            selected_slot = None
    selected_slot = _ensure_active_timeslot(selected_slot, t)

    created = 0
    conflicts = 0
    with transaction.atomic():
        cur = start_d
        while cur <= end_d:
            if cur.weekday() in selected_days:
                try:
                    SpotSchedule.objects.create(
                        spot=spot,
                        time_slot=selected_slot,
                        broadcast_date=cur,
                        broadcast_time=t,
                        price=Decimal('0'),
                        is_broadcasted=False,
                    )
                    created += 1
                except IntegrityError:
                    conflicts += 1
            cur += timezone.timedelta(days=1)

    if created > 0 and spot.status == 'approved':
        spot.status = 'scheduled'
        spot.save(update_fields=['status'])

    # Émettre une mise à jour pour le dernier créneau si possible (indicatif)
    try:
        last_sched = spot.schedules.order_by('-broadcast_date', '-broadcast_time').first()
        if last_sched:
            _emit_planning_upsert(last_sched)
    except Exception:
        pass

    # Historique
    CampaignHistory.objects.create(
        campaign=spot.campaign,
        action='bulk_scheduled',
        description=f'Programmations multiples: {created} créé(s), {conflicts} conflit(s).',
        user=request.user,
    )

    # Réponse adaptée: JSON pour AJAX, sinon redirection avec message
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return JsonResponse({'ok': True, 'created': created, 'conflicts': conflicts})
    else:
        messages.success(request, f"Programmations ajoutées: {created}, conflits: {conflicts}")
        return redirect('diffusion_spot_detail', spot_id=spot.id)


@login_required
def planning(request):
    """Planning avec vues jour/semaine/mois"""
    view = (request.GET.get('view') or 'week').lower()
    today = timezone.localdate()
    # Afficher les programmations pour spots programmés/approuvés/diffusés
    schedules = SpotSchedule.objects.select_related('spot', 'time_slot').filter(spot__status__in=['scheduled', 'approved', 'broadcasted'])

    if view == 'day':
        target = today
        schedules = schedules.filter(broadcast_date=target).order_by('broadcast_time')
    elif view == 'month':
        target_month_start = today.replace(day=1)
        # prochain mois
        if target_month_start.month == 12:
            next_month_start = target_month_start.replace(year=target_month_start.year+1, month=1)
        else:
            next_month_start = target_month_start.replace(month=target_month_start.month+1)
        schedules = schedules.filter(broadcast_date__gte=target_month_start, broadcast_date__lt=next_month_start).order_by('broadcast_date','broadcast_time')
    else:
        # week
        start_week = today - timezone.timedelta(days=today.weekday())
        end_week = start_week + timezone.timedelta(days=7)
        schedules = schedules.filter(broadcast_date__gte=start_week, broadcast_date__lt=end_week).order_by('broadcast_date','broadcast_time')

    ctx = _base_context(request.user)
    ctx.update({
        'view': view,
        'schedules': schedules,
        'today': today,
        'week_days': [today - timezone.timedelta(days=today.weekday()) + timezone.timedelta(days=i) for i in range(7)] if view == 'week' else [],
    })
    return render(request, 'spot/diffusion/planning.html', ctx)


@login_required
def planning_move(request):
    """API pour déplacer un créneau (drag-and-drop ou autosave) vers une nouvelle date/heure.
    Valide les contraintes: campagne, format, passé, et conflits éventuels.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)
    sched_id = request.POST.get('schedule_id')
    new_date = request.POST.get('broadcast_date')
    new_time = request.POST.get('broadcast_time')
    if not sched_id or not new_date:
        return JsonResponse({'ok': False, 'error': 'missing_params'}, status=400)
    try:
        sched = SpotSchedule.objects.select_related('spot', 'spot__campaign', 'time_slot').get(
            id=int(sched_id) if str(sched_id).isdigit() else sched_id
        )
    except SpotSchedule.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)

    # Parsing sécurisé
    try:
        d = timezone.datetime.fromisoformat(new_date).date()
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_date'}, status=422)

    t = None
    if new_time:
        try:
            t = timezone.datetime.fromisoformat(f"1970-01-01T{new_time}").time()
        except Exception:
            return JsonResponse({'ok': False, 'error': 'invalid_time'}, status=422)

    spot = sched.spot
    campaign = spot.campaign

    # Validation droits d'accès: spots approuvés ou programmés
    if getattr(spot, 'status', None) not in ['approved', 'scheduled']:
        return JsonResponse({'ok': False, 'error': 'spot_not_validated'}, status=403)

    # Interdire modification le jour en cours
    if sched.broadcast_date == timezone.localdate():
        return JsonResponse({'ok': False, 'error': 'today_locked'}, status=403)

    # Validation: date dans la campagne (avec possibilité d'override par diffuseur/admin)
    if getattr(campaign, 'start_date', None) and d < campaign.start_date:
        return JsonResponse({'ok': False, 'error': 'before_campaign_start'}, status=422)
    allow_ext_param = request.POST.get('allow_extension')
    allow_extension = str(allow_ext_param).lower() in ['1', 'true', 't', 'yes', 'y']
    try:
        can_override_user = (
            (hasattr(request.user, 'is_diffuser') and request.user.is_diffuser()) or
            (hasattr(request.user, 'is_admin') and request.user.is_admin()) or
            getattr(request.user, 'is_superuser', False)
        )
    except Exception:
        can_override_user = getattr(request.user, 'is_superuser', False)
    if getattr(campaign, 'end_date', None) and d > campaign.end_date and not (allow_extension and can_override_user):
        return JsonResponse({'ok': False, 'error': 'after_campaign_end'}, status=422)

    # Validation: ne pas programmer dans le passé (sauf déjà diffusé)
    try:
        final_time = t or sched.broadcast_time
        dt = timezone.make_aware(timezone.datetime.combine(d, final_time))
        if dt < timezone.now() and not sched.is_broadcasted:
            return JsonResponse({'ok': False, 'error': 'past_time'}, status=422)
    except Exception:
        # Si pas d'heure fournie et absente, ignorer cette validation
        pass

    # Conflit: même créneau/date/heure
    conflict = None
    if final_time := (t or sched.broadcast_time):
        conflict = SpotSchedule.objects.filter(
            time_slot=sched.time_slot,
            broadcast_date=d,
            broadcast_time=final_time
        ).exclude(id=sched.id).select_related('spot').first()
        if conflict:
            return JsonResponse({'ok': False, 'error': 'schedule_conflict', 'conflict_with': getattr(conflict.spot, 'title', '')}, status=409)

    # Appliquer mise à jour
    try:
        with transaction.atomic():
            sched.broadcast_date = d
            if t:
                sched.broadcast_time = t
            sched.save(update_fields=['broadcast_date'] + (['broadcast_time'] if t else []))
            if allow_extension and getattr(campaign, 'end_date', None) and d > campaign.end_date and can_override_user:
                CampaignHistory.objects.create(
                    campaign=campaign,
                    action='updated',
                    description=f"Programmation étendue au-delà de la fin de campagne: nouvelle date {d}, fin initiale {campaign.end_date} (par {request.user.username}).",
                    user=request.user,
                )
                try:
                    Notification.objects.create(
                        user=campaign.client,
                        title="Extension de diffusion au-delà de la campagne",
                        message=f"Le diffuseur a programmé le spot '{spot.title}' le {d} en dehors des dates de campagne (fin: {campaign.end_date}).",
                        type='warning',
                        related_campaign=campaign,
                        related_spot=spot,
                    )
                except Exception:
                    pass
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    # Notifier Planning
    try:
        _emit_planning_upsert(sched)
    except Exception:
        pass

    return JsonResponse({'ok': True, 'item': _planning_item_payload(sched)})


@login_required
def planning_delete(request):
    """Supprimer une programmation de spot"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method_not_allowed'}, status=405)
    sched_id = request.POST.get('schedule_id')
    if not sched_id:
        return JsonResponse({'ok': False, 'error': 'missing_params'}, status=400)
    try:
        sched = SpotSchedule.objects.select_related('spot').get(id=int(sched_id) if str(sched_id).isdigit() else sched_id)
    except SpotSchedule.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
    # Validation droits d'accès: autoriser les spots approuvés, programmés ou déjà diffusés
    # (la suppression reste bloquée si le créneau est déjà diffusé ou le jour J)
    if getattr(sched.spot, 'status', None) not in {'approved', 'scheduled', 'broadcasted'}:
        return JsonResponse({'ok': False, 'error': 'spot_not_validated'}, status=403)
    # Interdire suppression le jour en cours
    if sched.broadcast_date == timezone.localdate():
        return JsonResponse({'ok': False, 'error': 'today_locked'}, status=403)
    # Interdire suppression si déjà diffusé
    if sched.is_broadcasted:
        return JsonResponse({'ok': False, 'error': 'already_broadcasted'}, status=422)
    try:
        spot = sched.spot
        sched.delete()
        # Historiser
        CampaignHistory.objects.create(
            campaign=spot.campaign,
            action='deleted',
            description=f"Programmation supprimée pour '{spot.title}'",
            user=request.user,
        )
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True})


@login_required
def downloads(request):
    """Page Téléchargements: liste des spots avec fichiers"""
    # Limiter aux spots validés (ou diffusés) disposant de médias
    qs = Spot.objects.filter(
        Q(video_file__isnull=False) | Q(image_file__isnull=False),
        status__in=['approved', 'broadcasted']
    ).select_related('campaign__client').order_by('-updated_at')
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(campaign__client__username__icontains=q))

    def _size_human(f):
        try:
            size = getattr(f, 'size', None)
            if not size:
                return '-'
            if size < 1024:
                return f"{size} B"
            if size < 1024*1024:
                return f"{size//1024} KB"
            return f"{round(size/1024/1024,2)} MB"
        except Exception:
            return '-'

    downloads = []
    for s in qs[:200]:
        file_field = s.video_file or s.image_file
        downloads.append({
            'id': s.id,
            'title': s.title,
            'client': getattr(getattr(s.campaign, 'client', None), 'username', ''),
            'size_human': _size_human(file_field),
            'status': 'nouveau' if (timezone.now() - getattr(s, 'created_at', timezone.now())).days < 7 else 'mis à jour',
            'url': (file_field.url if (file_field and getattr(file_field, 'name', '')) else ''),
        })

    ctx = _base_context(request.user)
    ctx.update({'downloads': downloads, 'query': q or ''})
    return render(request, 'spot/diffusion/downloads.html', ctx)


@login_required
def downloads_zip(request):
    """Téléchargement par lot des médias des spots sélectionnés en ZIP"""
    if request.method != 'POST':
        return redirect('diffusion_downloads')

    ids = request.POST.getlist('spot_ids')
    if not ids:
        return redirect('diffusion_downloads')

    spots = Spot.objects.filter(id__in=ids)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for spot in spots:
            file_field = spot.video_file or spot.image_file
            file_path = getattr(file_field, 'path', None)
            file_name = os.path.basename(getattr(file_field, 'name', str(spot.id)))
            arcname = f"{spot.title[:50].replace(' ', '_')}_{file_name}"
            try:
                if file_path and os.path.exists(file_path):
                    zf.write(file_path, arcname=arcname)
                else:
                    data = getattr(file_field, 'read', None)
                    if callable(data):
                        content = data()
                        zf.writestr(arcname, content)
            except Exception:
                continue

    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="spots_medias.zip"'
    return response


@login_required
def download_spot_media(request, spot_id):
    """Télécharger le média (vidéo/image) d'un spot individuel"""
    try:
        spot = get_object_or_404(Spot, id=spot_id)
        file_field = spot.video_file or spot.image_file
        file_path = getattr(file_field, 'path', None)
        file_name = os.path.basename(getattr(file_field, 'name', str(spot.id)))
        if file_path and os.path.exists(file_path):
            f = open(file_path, 'rb')
            resp = FileResponse(f)
            resp['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return resp
        # Fallback: si le stockage ne permet pas l'accès par chemin, rediriger vers l'URL du fichier
        file_url = getattr(file_field, 'url', '')
        if file_url:
            return redirect(file_url)
        messages.error(request, "Aucun média disponible pour ce spot.")
        return redirect('diffusion_downloads')
    except Exception:
        messages.error(request, "Téléchargement impossible pour ce spot.")
        return redirect('diffusion_downloads')


@login_required
def kpi_api(request):
    today = timezone.localdate()
    data = {
        'spots_today': SpotSchedule.objects.filter(broadcast_date=today).count(),
        'late_spots': SpotSchedule.objects.filter(broadcast_date__lt=today, is_broadcasted=False).count(),
        'week': {}
    }
    start_week = today - timezone.timedelta(days=today.weekday())
    for i in range(7):
        d = start_week + timezone.timedelta(days=i)
        data['week'][d.strftime('%a %d/%m')] = SpotSchedule.objects.filter(broadcast_date=d).count()
    return JsonResponse(data)


@login_required
def export_spots_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="spots_diffusion.csv"'
    writer = csv.writer(response)
    writer.writerow(['Titre', 'Client', 'Type', 'Statut', 'Durée (s)', 'Date diffusion', 'Heure diffusion'])
    # Exporter uniquement les spots validés (ou diffusés)
    qs = Spot.objects.select_related('campaign__client').filter(status__in=['approved', 'broadcasted']).order_by('-created_at')
    for spot in qs:
        sched = spot.schedules.order_by('broadcast_date', 'broadcast_time').first()
        writer.writerow([
            spot.title,
            getattr(spot.campaign.client, 'username', ''),
            spot.media_type,
            spot.status,
            spot.duration_seconds or '',
            getattr(sched, 'broadcast_date', ''),
            getattr(sched, 'broadcast_time', ''),
        ])
    return response


@login_required
def export_spots_xlsx(request):
    """Export Excel des spots (si openpyxl installé), sinon redirection CSV"""
    try:
        from openpyxl import Workbook
    except Exception:
        return redirect('diffusion_export_spots_csv')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Spots'
    ws.append(['Titre', 'Client', 'Type', 'Statut', 'Durée (s)', 'Date diffusion', 'Heure diffusion'])

    qs = Spot.objects.select_related('campaign__client').all().order_by('-created_at')
    for spot in qs:
        sched = spot.schedules.order_by('broadcast_date', 'broadcast_time').first()
        ws.append([
            spot.title,
            getattr(spot.campaign.client, 'username', ''),
            spot.media_type,
            spot.status,
            spot.duration_seconds or '',
            getattr(sched, 'broadcast_date', ''),
            getattr(sched, 'broadcast_time', ''),
        ])

    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    resp = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="spots_diffusion.xlsx"'
    return resp
@login_required
def spots_late(request):
    """Liste des programmations dépassées (retards) pour les diffuseurs."""
    now = timezone.now()
    schedules = SpotSchedule.objects.select_related('spot', 'time_slot').filter(
        broadcast_date__lte=now.date(),
        is_broadcasted=False,
        spot__status__in=['approved', 'scheduled']
    ).order_by('-broadcast_date', '-broadcast_time')

    # Filtrer seulement celles dont l'heure est passée
    late = []
    for s in schedules[:500]:
        dt = timezone.make_aware(timezone.datetime.combine(s.broadcast_date, s.broadcast_time))
        if dt < now:
            late.append({
                'id': s.id,
                'spot_id': s.spot.id,
                'title': s.spot.title,
                'client': getattr(getattr(s.spot.campaign, 'client', None), 'username', ''),
                'broadcast_date': s.broadcast_date,
                'broadcast_time': s.broadcast_time,
                'time_slot': getattr(s.time_slot, 'name', ''),
            })

    ctx = _base_context(request.user)
    ctx.update({'late_schedules': late, 'late_count': len(late)})
    return render(request, 'spot/diffusion/spots_late.html', ctx)