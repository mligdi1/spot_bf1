from django.conf import settings
from .models import Notification

def widget_config(request):
    """Expose WhatsApp widget configuration to all templates."""
    config = {
        'enabled': getattr(settings, 'WHATSAPP_WIDGET_ENABLED', False),
        'phone': getattr(settings, 'WHATSAPP_PHONE', ''),
        'message': getattr(settings, 'WHATSAPP_DEFAULT_MESSAGE', ''),
        'position': getattr(settings, 'WHATSAPP_WIDGET_POSITION', 'bottom-right'),
        'color': getattr(settings, 'WHATSAPP_WIDGET_COLOR', '#25D366'),
        'size': getattr(settings, 'WHATSAPP_WIDGET_SIZE', 'md'),
    }
    return {
        'WHATSAPP_WIDGET': config
    }

def chatbot_config(request):
    """Expose chatbot configuration to all templates."""
    user = getattr(request, 'user', None)
    base_suggestions = list(getattr(settings, 'CHATBOT_DEFAULT_SUGGESTIONS', []) or [])
    extra: list[str] = []
    if user and getattr(user, 'is_authenticated', False):
        if getattr(user, 'is_admin', lambda: False)():
            extra = [
                'Console admin',
                'Demandes de couverture',
                'Correspondance',
            ]
        elif getattr(user, 'is_editorial_manager', lambda: False)():
            extra = [
                'Interface Rédaction',
                'Demandes validées',
                'Planning rédaction',
                'Gérer les journalistes',
            ]
        elif getattr(user, 'is_diffuser', lambda: False)():
            extra = [
                'Interface Diffusion',
                'Spots en retard',
                'Planning diffusion',
            ]
        else:
            extra = [
                'Demande de couverture',
                'Mes notifications',
                'Mon profil',
            ]

    suggestions = []
    for s in [*base_suggestions, *extra]:
        s2 = (s or '').strip()
        if not s2 or s2 in suggestions:
            continue
        suggestions.append(s2)
    suggestions = suggestions[:10]

    config = {
        'enabled': getattr(settings, 'CHATBOT_ENABLED', False),
        'provider': getattr(settings, 'CHATBOT_PROVIDER', 'none'),
        'escalate_mode': getattr(settings, 'CHATBOT_ESCLATE_MODE', 'contact'),
        'suggestions': suggestions,
    }
    return {
        'CHATBOT': config
    }

def notifications_summary(request):
    """Expose le compteur de notifications non lues à toutes les templates."""
    count = 0
    thread_count = 0
    if getattr(request, 'user', None) and request.user.is_authenticated:
        try:
            count = Notification.objects.filter(user=request.user, is_read=False).count()
            thread_count = Notification.objects.filter(user=request.user, is_read=False, related_thread__isnull=False).count()
        except Exception:
            count = 0
            thread_count = 0
    return {
        'NOTIFS_UNREAD_COUNT': count,
        'THREAD_NOTIFS_UNREAD_COUNT': thread_count,
    }
