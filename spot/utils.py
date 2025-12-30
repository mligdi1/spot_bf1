"""
Utilitaires pour l'application BF1 TV
"""

import os
import uuid
import json
import secrets
import urllib.request
import urllib.error
import urllib.parse
import logging
import base64
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime, timedelta


def generate_unique_filename(instance, filename):
    """
    Génère un nom de fichier unique pour les uploads
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)


def calculate_campaign_cost(duration, time_slot_multiplier, broadcast_count, base_price=1000):
    """
    Calcule le coût d'une campagne publicitaire
    
    Args:
        duration (int): Durée du spot en secondes
        time_slot_multiplier (Decimal): Multiplicateur du créneau horaire
        broadcast_count (int): Nombre de diffusions
        base_price (int): Prix de base par seconde
    
    Returns:
        dict: Détail du calcul du coût
    """
    duration_price = Decimal(str(base_price)) * Decimal(str(duration))
    total_price = duration_price * time_slot_multiplier * Decimal(str(broadcast_count))
    tax_rate = Decimal('0.18')  # 18% TVA
    tax_amount = total_price * tax_rate
    final_price = total_price + tax_amount
    
    return {
        'base_price': Decimal(str(base_price)),
        'duration_price': duration_price,
        'time_multiplier': time_slot_multiplier,
        'total_price': total_price,
        'tax_amount': tax_amount,
        'final_price': final_price,
    }


def send_notification_email(user, subject, message, campaign=None, attachments=None):
    """
    Envoie un email de notification à un utilisateur
    
    Args:
        user: Utilisateur destinataire
        subject (str): Sujet de l'email
        message (str): Message de l'email
        campaign: Campagne liée (optionnel)
    """
    try:
        context = {
            'user': user,
            'message': message,
            'campaign': campaign,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        html_message = render_to_string('emails/notification.html', context)
        plain_message = render_to_string('emails/notification.txt', context)
        
        email = EmailMultiAlternatives(
            subject=f'[BF1 TV] {subject}',
            body=plain_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bf1tv.bf'),
            to=[user.email],
        )
        email.attach_alternative(html_message, 'text/html')
        for att in attachments or []:
            try:
                filename, content, mimetype = att
                email.attach(filename, content, mimetype)
            except Exception:
                pass
        email.send(fail_silently=False)
        
        return True
    except Exception as e:
        logging.getLogger('spot').error('Erreur envoi email', exc_info=True)
        return False


def normalize_phone(phone):
    if not phone:
        return ''
    raw = str(phone).strip()
    keep = []
    for ch in raw:
        if ch.isdigit():
            keep.append(ch)
        elif ch == '+' and not keep:
            keep.append(ch)
    cleaned = ''.join(keep)
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    return cleaned


def send_sms(phone, message):
    api_url = getattr(settings, 'SPOT_SMS_API_URL', '') or ''
    token = getattr(settings, 'SPOT_SMS_API_TOKEN', '') or ''
    sender = getattr(settings, 'SPOT_SMS_SENDER', '') or ''
    to_phone = normalize_phone(phone)
    if not api_url:
        return False, None, 'SMS backend non configuré (SPOT_SMS_API_URL manquant)'
    payload = {
        'to': to_phone,
        'message': message,
    }
    if sender:
        payload['sender'] = sender
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read() or b''
        try:
            parsed = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            parsed = {}
        msg_id = parsed.get('id') or parsed.get('message_id') or parsed.get('sid')
        return True, msg_id, ''
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8')
        except Exception:
            err_body = str(e)
        logging.getLogger('spot').error('HTTPError envoi SMS: %s', err_body)
        return False, None, err_body
    except Exception as e:
        logging.getLogger('spot').error('Erreur envoi SMS', exc_info=True)
        return False, None, str(e)


def send_whatsapp(phone, message, attachments=None):
    api_url = getattr(settings, 'SPOT_WHATSAPP_API_URL', '') or ''
    token = getattr(settings, 'SPOT_WHATSAPP_API_TOKEN', '') or ''
    sender = getattr(settings, 'SPOT_WHATSAPP_SENDER', '') or ''
    to_phone = normalize_phone(phone)
    if not api_url:
        return False, None, 'WhatsApp backend non configuré (SPOT_WHATSAPP_API_URL manquant)'
    payload = {
        'to': to_phone,
        'message': message,
    }
    if sender:
        payload['sender'] = sender
    att_list = []
    for att in attachments or []:
        try:
            filename, content, mimetype = att
            att_list.append(
                {
                    'filename': filename,
                    'mimetype': mimetype,
                    'content_base64': base64.b64encode(content).decode('ascii'),
                }
            )
        except Exception:
            pass
    if att_list:
        payload['attachments'] = att_list
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read() or b''
        try:
            parsed = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            parsed = {}
        msg_id = parsed.get('id') or parsed.get('message_id') or parsed.get('sid')
        return True, msg_id, ''
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode('utf-8')
        except Exception:
            err_body = str(e)
        logging.getLogger('spot').error('HTTPError envoi WhatsApp: %s', err_body)
        return False, None, err_body
    except Exception as e:
        logging.getLogger('spot').error('Erreur envoi WhatsApp', exc_info=True)
        return False, None, str(e)


def build_coverage_pdf(coverage):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title='Détails de couverture',
        author='BF1 TV',
    )
    styles = getSampleStyleSheet()
    story = []

    title = str(getattr(coverage, 'event_title', '') or 'Demande de couverture').strip()
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 10))

    def _kv_table(rows):
        data = [[Paragraph(f'<b>{k}</b>', styles['BodyText']), Paragraph(v, styles['BodyText'])] for k, v in rows]
        t = Table(data, colWidths=[4.2 * cm, 11.8 * cm])
        t.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]
            )
        )
        return t

    def _s(v):
        return str(v or '').strip()

    event_rows = []
    event_rows.append(('Type', _s(getattr(coverage, 'get_event_type_display', lambda: '')())))
    if _s(getattr(coverage, 'event_type', '')) == 'other':
        event_rows.append(('Précision', _s(getattr(coverage, 'event_type_other', ''))))
    event_rows.append(('Date', coverage.event_date.strftime('%d/%m/%Y') if getattr(coverage, 'event_date', None) else '—'))
    start_s = coverage.start_time.strftime('%H:%M') if getattr(coverage, 'start_time', None) else '—'
    end_s = coverage.end_time.strftime('%H:%M') if getattr(coverage, 'end_time', None) else ''
    event_rows.append(('Horaire', f'{start_s} – {end_s}'.strip(' –') if end_s else start_s))
    event_rows.append(('Adresse', _s(getattr(coverage, 'address', '')) or '—'))
    meeting = _s(getattr(coverage, 'meeting_point', ''))
    if meeting:
        event_rows.append(('Point de rencontre', meeting))
    desc = _s(getattr(coverage, 'description', ''))
    if desc:
        event_rows.append(('Description', desc))
    story.append(Paragraph('Événement', styles['Heading2']))
    story.append(_kv_table(event_rows))
    story.append(Spacer(1, 12))

    contact_rows = []
    contact_rows.append(('Nom', _s(getattr(coverage, 'contact_name', '')) or '—'))
    contact_rows.append(('Téléphone', _s(getattr(coverage, 'contact_phone', '')) or '—'))
    contact_rows.append(('Email', _s(getattr(coverage, 'contact_email', '')) or '—'))
    other = _s(getattr(coverage, 'other_contacts', ''))
    if other:
        contact_rows.append(('Autres contacts', other))
    story.append(Paragraph('Contacts', styles['Heading2']))
    story.append(_kv_table(contact_rows))
    story.append(Spacer(1, 12))

    cov_rows = []
    cov_rows.append(('Type', _s(getattr(coverage, 'get_coverage_type_display', lambda: '')())))
    cov_rows.append(('Urgence', _s(getattr(coverage, 'get_urgency_level_display', lambda: '')())))
    cov_rows.append(('Statut', _s(getattr(coverage, 'get_status_display', lambda: '')())))
    deadline = getattr(coverage, 'response_deadline', None)
    cov_rows.append(('Réponse attendue avant', deadline.strftime('%d/%m/%Y') if deadline else '—'))
    cov_rows.append(('Informations confirmées', 'Oui' if getattr(coverage, 'confirm_info', False) else 'Non'))
    objective = _s(getattr(coverage, 'coverage_objective', ''))
    if objective:
        cov_rows.append(('Objectif', objective))
    story.append(Paragraph('Couverture', styles['Heading2']))
    story.append(_kv_table(cov_rows))
    story.append(Spacer(1, 12))

    attachments = []
    try:
        for att in coverage.attachments.all():
            name = ''
            try:
                name = att.file.name
            except Exception:
                name = ''
            if name:
                attachments.append(name)
    except Exception:
        attachments = []
    story.append(Paragraph('Pièces jointes', styles['Heading2']))
    story.append(
        Paragraph('<br/>'.join([_s(a) for a in attachments]) if attachments else 'Aucune pièce jointe.', styles['BodyText'])
    )

    doc.build(story)
    content = buf.getvalue()
    buf.close()
    date_s = coverage.event_date.strftime('%Y%m%d') if getattr(coverage, 'event_date', None) else 'date'
    filename = f'bf1-couverture-{date_s}.pdf'
    return filename, content, 'application/pdf'


def send_assignment_notification_email(to_email, recipient_label, subject, attachments=None):
    try:
        plain = f'Bonjour {recipient_label},\n\nVeuillez trouver en pièce jointe la fiche complète de la couverture assignée.\n\nCordialement,\nBF1 TV'
        html = f'<p>Bonjour {recipient_label},</p><p>Veuillez trouver en pièce jointe la fiche complète de la couverture assignée.</p><p>Cordialement,<br/>BF1 TV</p>'
        email = EmailMultiAlternatives(
            subject=f'[BF1 TV] {subject}',
            body=plain,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bf1tv.bf'),
            to=[to_email],
        )
        email.attach_alternative(html, 'text/html')
        for att in attachments or []:
            try:
                filename, content, mimetype = att
                email.attach(filename, content, mimetype)
            except Exception:
                pass
        email.send(fail_silently=False)
        return True
    except Exception:
        logging.getLogger('spot').error('Erreur envoi email assignation', exc_info=True)
        return False


def build_coverage_ics(coverage):
    tzid = getattr(settings, 'SPOT_ICS_TZID', 'Africa/Ouagadougou')
    start_dt = datetime.combine(coverage.event_date, coverage.start_time)
    if coverage.end_time:
        end_dt = datetime.combine(coverage.event_date, coverage.end_time)
    else:
        end_dt = start_dt + timedelta(hours=1)
    uid = f'{coverage.id}@bf1tv.bf'
    stamp = timezone.now().strftime('%Y%m%dT%H%M%SZ')
    dtstart = start_dt.strftime('%Y%m%dT%H%M%S')
    dtend = end_dt.strftime('%Y%m%dT%H%M%S')
    summary = str(coverage.event_title or 'Couverture BF1').replace('\n', ' ').strip()
    location = str(coverage.address or '').replace('\n', ' ').strip()
    description = str(coverage.description or '').replace('\n', ' ').strip()
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//BF1 TV//SPOT//FR',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{stamp}',
        f'DTSTART;TZID={tzid}:{dtstart}',
        f'DTEND;TZID={tzid}:{dtend}',
        f'SUMMARY:{summary}',
        f'LOCATION:{location}',
        f'DESCRIPTION:{description}',
        'END:VEVENT',
        'END:VCALENDAR',
        '',
    ]
    content = '\r\n'.join(lines).encode('utf-8')
    filename = f'bf1-couverture-{coverage.event_date.strftime("%Y%m%d")}.ics'
    return filename, content, 'text/calendar; charset=utf-8'


def create_assignment_notification_campaigns(assignment, created_by=None):
    from .models import AssignmentNotificationCampaign, AssignmentNotificationAttempt, AssignmentLog

    coverage = assignment.coverage
    now = timezone.now()
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')

    def _new_code():
        return str(secrets.randbelow(1000000)).zfill(6)

    def _message_base(recipient_label):
        return 'Assignation BF1 TV — fiche de couverture en PDF.'

    campaigns = []
    recipients = []
    if assignment.journalist:
        recipients.append(('journalist', assignment.journalist.name or 'Journaliste', assignment.journalist.email, assignment.journalist.phone))
    if assignment.driver:
        recipients.append(('driver', assignment.driver.name or 'Chauffeur', None, assignment.driver.phone))

    for kind, label, email_addr, phone in recipients:
        to_email = email_addr or None
        to_phone = normalize_phone(phone) or None
        campaign = (
            AssignmentNotificationCampaign.objects.filter(
                assignment=assignment,
                recipient_kind=kind,
                to_email=to_email,
                to_phone=to_phone,
                status__in=['active', 'confirmed'],
            )
            .order_by('-created_at')
            .first()
        )
        if not campaign:
            code = _new_code()
            campaign = AssignmentNotificationCampaign.objects.create(
                assignment=assignment,
                recipient_kind=kind,
                to_email=to_email,
                to_phone=to_phone,
                confirm_code=code,
                status='active',
                next_attempt_at=None,
            )
        if to_email and not AssignmentNotificationAttempt.objects.filter(campaign=campaign, channel='email').exists():
            AssignmentNotificationAttempt.objects.create(
                campaign=campaign,
                channel='email',
                status='queued',
                to=to_email,
                subject='Assignation couverture',
                body='PDF',
            )
        AssignmentLog.objects.create(assignment=assignment, label='Notifications prêtes', note=f'{kind}')
        campaigns.append(campaign)

    return campaigns


def process_due_assignment_notification_campaigns(now=None, limit=100):
    from .models import AssignmentNotificationCampaign, AssignmentNotificationAttempt, AssignmentLog

    now = now or timezone.now()
    qs = AssignmentNotificationCampaign.objects.select_related('assignment', 'assignment__coverage').filter(
        status='active',
        confirmed_at__isnull=True,
        next_attempt_at__isnull=False,
        next_attempt_at__lte=now,
    ).order_by('next_attempt_at')[:limit]

    processed = 0
    for campaign in qs:
        phone = campaign.to_phone or ''
        if not phone:
            campaign.next_attempt_at = None
            campaign.save(update_fields=['next_attempt_at', 'updated_at'])
            continue

        coverage = campaign.assignment.coverage
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        confirm_url = f'{site_url}/assignments/confirm/{campaign.id}/{campaign.confirm_code}/'
        base = (
            f'Assignation BF1 TV: {coverage.event_title} le {coverage.event_date} '
            f'à {coverage.start_time.strftime("%H:%M")} — {coverage.address}. '
            f'Code {campaign.confirm_code}. Lien {confirm_url}'
        )
        if campaign.reminder_count == 0:
            text = base
            next_at = now + timedelta(minutes=30)
        else:
            text = f'RAPPEL — {base}'
            next_at = None

        ok, msg_id, err = send_sms(phone, text)
        AssignmentNotificationAttempt.objects.create(
            campaign=campaign,
            channel='sms',
            status='sent' if ok else 'failed',
            to=phone,
            body=text,
            provider=getattr(settings, 'SPOT_SMS_PROVIDER', ''),
            provider_message_id=msg_id or '',
            error='' if ok else err,
            sent_at=timezone.now() if ok else None,
        )
        AssignmentLog.objects.create(assignment=campaign.assignment, label='Relance SMS', note=f'{campaign.recipient_kind} — {"ok" if ok else "failed"}')
        campaign.reminder_count = min(campaign.reminder_count + 1, 2)
        campaign.next_attempt_at = next_at
        if not next_at and campaign.reminder_count >= 2:
            campaign.status = 'expired'
        campaign.save(update_fields=['reminder_count', 'next_attempt_at', 'status', 'updated_at'])
        processed += 1

    return processed


def confirm_assignment_notification_campaign(campaign, via):
    from .models import AssignmentNotificationAttempt, AssignmentLog

    if campaign.confirmed_at:
        return False
    campaign.confirmed_at = timezone.now()
    campaign.confirmed_via = via or ''
    campaign.status = 'confirmed'
    campaign.next_attempt_at = None
    campaign.save(update_fields=['confirmed_at', 'confirmed_via', 'status', 'next_attempt_at', 'updated_at'])
    AssignmentNotificationAttempt.objects.create(
        campaign=campaign,
        channel=via if via in {'sms', 'web'} else 'web',
        status='confirmed',
        to=campaign.to_phone or campaign.to_email or '',
        body='confirmed',
        sent_at=timezone.now(),
    )
    AssignmentLog.objects.create(assignment=campaign.assignment, label='Confirmation reçue', note=f'{campaign.recipient_kind} — {via}')
    return True


def format_currency(amount, currency='FCFA'):
    """
    Formate un montant en devise
    
    Args:
        amount (Decimal): Montant à formater
        currency (str): Devise
    
    Returns:
        str: Montant formaté
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    
    return f"{amount:,.0f} {currency}"


def get_campaign_status_color(status):
    """
    Retourne la couleur CSS pour un statut de campagne
    
    Args:
        status (str): Statut de la campagne
    
    Returns:
        str: Classes CSS pour la couleur
    """
    colors = {
        'draft': 'bg-gray-100 text-gray-800',
        'pending': 'bg-yellow-100 text-yellow-800',
        'approved': 'bg-blue-100 text-blue-800',
        'rejected': 'bg-red-100 text-red-800',
        'active': 'bg-green-100 text-green-800',
        'completed': 'bg-gray-100 text-gray-800',
        'cancelled': 'bg-red-100 text-red-800',
    }
    return colors.get(status, 'bg-gray-100 text-gray-800')


def get_spot_status_color(status):
    """
    Retourne la couleur CSS pour un statut de spot
    
    Args:
        status (str): Statut du spot
    
    Returns:
        str: Classes CSS pour la couleur
    """
    colors = {
        'uploaded': 'bg-blue-100 text-blue-800',
        'pending_review': 'bg-yellow-100 text-yellow-800',
        'approved': 'bg-green-100 text-green-800',
        'rejected': 'bg-red-100 text-red-800',
        'scheduled': 'bg-purple-100 text-purple-800',
        'broadcasted': 'bg-green-100 text-green-800',
    }
    return colors.get(status, 'bg-gray-100 text-gray-800')


def validate_video_file(file):
    """
    Valide un fichier vidéo uploadé
    
    Args:
        file: Fichier uploadé
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Vérifier la taille (max 100MB)
    max_size = 100 * 1024 * 1024  # 100MB
    if file.size > max_size:
        return False, "Le fichier est trop volumineux. Taille maximale: 100MB"
    
    # Vérifier l'extension
    allowed_extensions = ['.mp4', '.avi', '.mov', '.wmv']
    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension not in allowed_extensions:
        return False, f"Format non supporté. Formats acceptés: {', '.join(allowed_extensions)}"
    
    return True, None


def get_campaign_statistics():
    """
    Retourne les statistiques générales des campagnes
    """
    from .models import Campaign, User

    total_campaigns = Campaign.objects.count()
    active_campaigns = Campaign.objects.filter(status='active').count()
    pending_campaigns = Campaign.objects.filter(status='pending').count()
    total_clients = User.objects.filter(role='client').count()

    return {
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'pending_campaigns': pending_campaigns,
        'total_clients': total_clients,
    }


def generate_invoice_number():
    """
    Génère un numéro de facture unique
    
    Returns:
        str: Numéro de facture
    """
    from .models import Invoice
    from datetime import datetime
    
    date_str = datetime.now().strftime('%Y%m%d')
    last_invoice = Invoice.objects.filter(
        invoice_number__startswith=f"BF1-{date_str}"
    ).order_by('-invoice_number').first()
    
    if last_invoice:
        last_num = int(last_invoice.invoice_number.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"BF1-{date_str}-{new_num:04d}"


def cleanup_old_files():
    """
    Nettoie les anciens fichiers temporaires
    """
    import glob
    from datetime import datetime, timedelta
    
    # Supprimer les fichiers temporaires de plus de 7 jours
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    if os.path.exists(temp_dir):
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for file_path in glob.glob(os.path.join(temp_dir, '*')):
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    try:
                        os.remove(file_path)
                        print(f"Fichier temporaire supprimé: {file_path}")
                    except OSError:
                        print(f"Impossible de supprimer: {file_path}")


def send_campaign_reminder():
    """
    Envoie des rappels pour les campagnes qui se terminent bientôt
    """
    from .models import Campaign
    
    # Campagnes qui se terminent dans 3 jours
    reminder_date = timezone.now().date() + timedelta(days=3)
    campaigns_ending_soon = Campaign.objects.filter(
        end_date=reminder_date,
        status='active'
    )
    
    for campaign in campaigns_ending_soon:
        subject = "Rappel: Votre campagne se termine bientôt"
        message = f"Votre campagne '{campaign.title}' se termine dans 3 jours ({campaign.end_date})."
        send_notification_email(campaign.client, subject, message, campaign)
