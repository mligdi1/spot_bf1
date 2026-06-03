# Vues supplémentaires pour l'application BF1 TV
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse

from .models import User, Campaign, Spot, CoverageRequest, CorrespondenceThread
from .services.chatbot import LocalLLMResponder, ChatMemory, append_persistent_memory
from .services.nlu import detect_intent, build_actions, guide_message
from .services.kb import search as kb_search
from .services.logs import log_unresolved
from .forms import SpotForm


def _chatbot_local_response(request, text: str):
    """Simple local rule-based responder (no external services)."""
    text_l = (text or '').lower()
    user = request.user if request.user.is_authenticated else None

    # Utiliser le nouveau système NLU même pour la réponse locale simple
    intent = detect_intent(text)
    
    def link(name):
        try:
            return reverse(name)
        except Exception:
            return '#'

    actions = build_actions(intent, user)
    
    if intent == 'about_site':
        resp = (
            "Bienvenue sur BF1 TV ! Ce projet digitalise la publicité télévisée au Burkina Faso. "
            "Vous pouvez créer des campagnes, gérer vos spots et suivre vos diffusions."
        )
    elif intent == 'create_campaign':
        resp = 'Pour créer une campagne, je peux vous guider étape par étape.'
    elif intent == 'upload_spot':
        resp = 'Pour téléverser votre spot, utilisez l’interface dédiée.'
    elif intent == 'view_broadcasts':
        resp = 'La planification des diffusions est accessible via le calendrier.'
    elif intent == 'support':
        resp = 'Je vous guide: parler à un agent humain, suivre vos échanges ou créer une discussion.'
    elif intent == 'pricing':
        resp = 'Voici nos tarifs et options disponibles.'
    elif intent == 'contact':
        resp = 'Je peux vous rediriger vers un conseiller humain.'
    else:
        resp = 'Je réfléchis à votre demande et vous propose des pistes utiles.'
        if not actions:
            actions.extend([
                {'label': 'Créer une campagne', 'href': link('campaign_spot_create')},
                {'label': 'Téléverser un spot', 'href': link('campaign_list')},
                {'label': 'Calendrier de diffusion', 'href': link('broadcast_grid')},
            ])

    return {
        'message': resp,
        'actions': actions,
        'escalate': 'contact',
        'escalate_url': link('contact_advisor'),
    }


@csrf_exempt
@require_POST
def chat_query(request):
    """Endpoint API pour le chatbot avancé (NLU + KB + LLM local).
    Retourne des actions typées (redirect, open_modal, ...) et un message de guidage.
    """
    try:
        payload = request.POST.get('text') or ''
        if not payload and request.body:
            import json
            data = json.loads(request.body.decode('utf-8'))
            payload = data.get('text', '')
        payload = (payload or '').strip()
        if not payload:
            return JsonResponse({'ok': False, 'error': 'empty'}, status=400)

        # Conversation memory
        mem = ChatMemory(request)
        history = mem.load()

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        intent = detect_intent(payload)
        actions = build_actions(intent, user=user)
        
        # Initialisation du répondeur pour les cas non gérés ou LLM
        responder = LocalLLMResponder()

        # Liste des intentions qui doivent utiliser les réponses détaillées du chatbot
        detailed_intents = {
            'about_site', 'bf1_tv', 'roles_permissions', 
            'technical_info', 'campaign_process', 'ad_types',
            'create_campaign', 'coverage_request', 'site_navigation', 'functional_elements'
        }

        if intent in detailed_intents:
            # Utiliser la réponse structurée et détaillée du chatbot
            rr = responder.reply(payload, history, user=user)
            msg = rr.get('message')
            actions = rr.get('actions')
        elif intent is None:
            rr = responder.reply(payload, history, user=user)
            msg = (rr or {}).get('message') or guide_message(intent, user=user)
        else:
            msg = guide_message(intent, user=user)

        # KB retrieval for precision (titles only)
        kb_hits = kb_search(payload, k=3)
        kb_titles = [h.get('title') for h in kb_hits]

        # Backward compatibility for existing widget expecting `href`
        for a in actions:
            if 'url' in a and 'href' not in a:
                a['href'] = a['url']
        result = {'ok': True, 'message': msg, 'actions': actions, 'kb': kb_titles}

        # Update memory
        mem.append('user', payload)
        if result.get('ok'):
            mem.append('assistant', result.get('message', ''))
            append_persistent_memory(payload, result.get('message', ''))
        else:
            log_unresolved(payload, {'intent': intent})

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
def pending_counts_api(request):
    """Retourne les compteurs de contenus en attente pour l'admin (JSON)."""
    if not request.user.is_admin():
        return JsonResponse({'error': 'unauthorized'}, status=403)
    data = {
        'count_campaigns_pending': Campaign.objects.filter(status='pending').count(),
        'count_spots_pending': Spot.objects.filter(status='pending_review').count(),
        'count_messages_pending': CorrespondenceThread.objects.filter(status='pending').count(),
        'count_coverages_pending': CoverageRequest.objects.filter(status='new').count(),
    }
    return JsonResponse(data)
