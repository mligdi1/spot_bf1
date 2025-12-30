# Vues supplémentaires pour l'application BF1 TV
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse
from decimal import Decimal

from .models import User, Campaign, Spot, CoverageRequest, TimeSlot, PricingRule
from .models import CorrespondenceThread
from .services.chatbot import LocalLLMResponder, ChatMemory, append_persistent_memory
from .services.nlu import detect_intent, build_actions, guide_message
from .services.kb import search as kb_search
from .services.logs import log_unresolved
from .forms import CampaignForm, SpotForm, CostSimulatorForm


def _chatbot_local_response(request, text: str):
    """Simple local rule-based responder (no external services)."""
    text_l = (text or '').lower()
    user = request.user if request.user.is_authenticated else None

    def link(name):
        try:
            return reverse(name)
        except Exception:
            return '#'

    actions = []
    resp = ''

    if any(k in text_l for k in ['campagne', 'créer', 'creation']):
        resp = 'Pour créer une campagne, je peux vous guider étape par étape.'
        actions.append({'label': 'Créer une campagne', 'href': link('campaign_spot_create')})
        actions.append({'label': 'Voir les campagnes', 'href': link('campaign_list')})
    elif any(k in text_l for k in ['spot', 'téléverser', 'upload']):
        resp = 'Pour téléverser votre spot, utilisez l’interface dédiée.'
        actions.append({'label': 'Téléverser un spot', 'href': link('campaign_list')})
    elif any(k in text_l for k in ['diffusion', 'calendrier', 'planifier']):
        resp = 'La planification des diffusions est accessible via le calendrier.'
        actions.append({'label': 'Voir le calendrier de diffusion', 'href': link('broadcast_grid')})
    elif any(k in text_l for k in ['correspondence', 'discussion', 'support']):
        resp = 'Je vous guide: parler à un agent humain, suivre vos échanges ou créer une discussion.'
        actions.append({'label': 'Parler à un agent humain', 'href': link('contact_advisor')})
        actions.append({'label': 'Suivre mes échanges', 'href': link('correspondence_list')})
        actions.append({'label': 'Créer une nouvelle discussion', 'href': link('correspondence_new')})
    elif any(k in text_l for k in ['tarif', 'prix']):
        resp = 'Voici nos tarifs et options disponibles.'
        actions.append({'label': 'Voir les tarifs', 'href': link('pricing_overview')})
    elif any(k in text_l for k in ['contact', 'humain', 'conseiller']):
        resp = 'Je peux vous rediriger vers un conseiller humain.'
        actions.append({'label': 'Parler à un agent humain', 'href': link('contact_advisor')})
    else:
        resp = 'Je réfléchis à votre demande et vous propose des pistes utiles.'
        actions.extend([
            {'label': 'Créer une campagne', 'href': link('campaign_spot_create')},
            {'label': 'Téléverser un spot', 'href': link('campaign_list')},
            {'label': 'Calendrier de diffusion', 'href': link('broadcast_grid')},
        ])

    # Personnalisation simple si connecté
    if user:
        actions.append({'label': 'Mes notifications', 'href': link('notifications')})
        actions.append({'label': 'Mon profil', 'href': link('profile')})

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
        msg = guide_message(intent, user=user)

        if intent is None:
            responder = LocalLLMResponder()
            rr = responder.reply(payload, history)
            msg = (rr or {}).get('message') or msg

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
def campaign_list(request):
    """Liste des campagnes"""
    user = request.user
    
    if user.is_client():
        campaigns = Campaign.objects.filter(client=user)
    else:
        campaigns = Campaign.objects.all()
    
    # Filtres
    status_filter = request.GET.get('status')
    if status_filter:
        campaigns = campaigns.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        campaigns = campaigns.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(campaigns.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    campaigns = paginator.get_page(page_number)
    
    context = {
        'campaigns': campaigns,
        'status_choices': Campaign.STATUS_CHOICES,
    }
    
    return render(request, 'spot/campaign_list.html', context)


@login_required
def campaign_create(request):
    """Création d'une nouvelle campagne"""
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.client = request.user
            campaign.save()
            messages.success(request, 'Campagne créée avec succès !')
            return redirect('campaign_detail', campaign_id=campaign.id)
    else:
        form = CampaignForm()
    
    return render(request, 'spot/campaign_create.html', {'form': form})


@login_required
def campaign_detail(request, campaign_id):
    """Détails d'une campagne"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Vérifier les permissions
    if request.user.is_client() and campaign.client != request.user:
        messages.error(request, 'Vous n\'avez pas accès à cette campagne.')
        return redirect('campaign_list')
    
    spots = campaign.spots.all()
    history = campaign.history.all()[:10]
    context = {
        'campaign': campaign,
        'spots': spots,
        'history': history,
    }
    return render(request, 'spot/campaign_detail.html', context)


@login_required
def spot_upload(request, campaign_id):
    """Téléchargement d'un spot"""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Vérifier les permissions
    if request.user.is_client() and campaign.client != request.user:
        messages.error(request, 'Vous n\'avez pas accès à cette campagne.')
        return redirect('campaign_list')
    
    if request.method == 'POST':
        form = SpotForm(request.POST, request.FILES)
        if form.is_valid():
            spot = form.save(commit=False)
            spot.campaign = campaign
            spot.save()
            messages.success(request, 'Spot téléchargé avec succès !')
            return redirect('campaign_detail', campaign_id=campaign.id)
    else:
        form = SpotForm()
    
    context = {
        'form': form,
        'campaign': campaign,
    }
    
    return render(request, 'spot/spot_upload.html', context)


@login_required
def cost_simulator(request):
    """Simulateur de coût publicitaire"""
    # Bloquer pour les administrateurs (interface client uniquement)
    try:
        if hasattr(request.user, 'is_admin') and request.user.is_admin():
            messages.error(request, "Cette fonctionnalité est réservée aux clients.")
            return redirect('dashboard')
    except Exception:
        return redirect('dashboard')
    tax_rate = Decimal('0.18')
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    pricing_rules = list(
        PricingRule.objects.filter(is_active=True)
        .order_by('duration_min')
        .values('duration_min', 'duration_max', 'base_price')
    )

    estimated_cost = None
    calculation_details = None

    if request.method == 'POST':
        form = CostSimulatorForm(request.POST)
        if form.is_valid():
            duration = form.cleaned_data['duration']
            time_slot = form.cleaned_data['time_slot']
            broadcast_count = form.cleaned_data['broadcast_count']

            base_price = None
            for r in pricing_rules:
                if r['duration_min'] <= duration <= r['duration_max']:
                    base_price = Decimal(str(r['base_price']))
                    break
            if base_price is None:
                base_price = Decimal('1000')

            time_multiplier = time_slot.price_multiplier
            subtotal = base_price * Decimal(duration) * Decimal(time_multiplier) * Decimal(broadcast_count)
            tax_amount = subtotal * tax_rate
            total = subtotal + tax_amount

            estimated_cost = total
            calculation_details = {
                'duration': duration,
                'base_price': base_price,
                'time_multiplier': time_multiplier,
                'broadcast_count': broadcast_count,
                'subtotal': subtotal,
                'tax': tax_amount,
                'total': total,
            }
    else:
        form = CostSimulatorForm()

    return render(
        request,
        'spot/cost_simulator.html',
        {
            'form': form,
            'time_slots': time_slots,
            'pricing_rules': pricing_rules,
            'tax_rate': tax_rate,
            'estimated_cost': estimated_cost,
            'calculation_details': calculation_details,
        },
    )


# Vue notifications dupliquée migrée dans views.py — supprimée pour éviter la confusion


# Vues pour les administrateurs
@login_required
def admin_campaign_approve(request, campaign_id):
    """Approbation d'une campagne par l'admin"""
    if not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            campaign.status = 'approved'
            campaign.approved_by = request.user
            campaign.approved_at = timezone.now()
            campaign.save()
            messages.success(request, 'Campagne approuvée !')
        elif action == 'reject':
            campaign.status = 'rejected'
            campaign.approved_by = request.user
            campaign.approved_at = timezone.now()
            campaign.rejection_reason = request.POST.get('rejection_reason', '')
            campaign.save()
            messages.success(request, 'Campagne rejetée !')
        
        return redirect('admin_dashboard')
    
    return render(request, 'spot/admin_campaign_approve.html', {'campaign': campaign})


@login_required
def admin_spot_approve(request, spot_id):
    """Approbation d'un spot par l'admin"""
    if not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    spot = get_object_or_404(Spot, id=spot_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            spot.status = 'approved'
            spot.approved_by = request.user
            spot.approved_at = timezone.now()
            spot.save()
            messages.success(request, 'Spot approuvé !')
        elif action == 'reject':
            spot.status = 'rejected'
            spot.approved_by = request.user
            spot.approved_at = timezone.now()
            spot.rejection_reason = request.POST.get('rejection_reason', '')
            spot.save()
            messages.success(request, 'Spot rejeté !')
        
        return redirect('admin_dashboard')
    
    return render(request, 'spot/admin_spot_approve.html', {'spot': spot})


@login_required
def admin_dashboard(request):
    """Tableau de bord administrateur"""
    if not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    # Statistiques générales
    stats = {
        'total_campaigns': Campaign.objects.count(),
        'pending_campaigns': Campaign.objects.filter(status='pending').count(),
        'active_campaigns': Campaign.objects.filter(status='active').count(),
        'total_clients': User.objects.filter(role='client').count(),
        # Compteurs pour bulles d'indicateurs
        'pending_spots': Spot.objects.filter(status='pending_review').count(),
        'pending_threads': CorrespondenceThread.objects.filter(status='pending').count(),
    }
    
    # Données récentes
    recent_campaigns = Campaign.objects.order_by('-created_at')[:10]
    pending_approvals = {
        'campaigns': Campaign.objects.filter(status='pending'),
        'spots': Spot.objects.filter(status='pending_review'),
    }
    
    context = {
        'stats': stats,
        'recent_campaigns': recent_campaigns,
        'pending_approvals': pending_approvals,
    }
    
    return render(request, 'spot/admin_dashboard.html', context)

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


@login_required
def admin_campaign_reject(request):
    """Vue pour rejeter des campagnes depuis l'admin avec une raison"""
    if not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('admin:index')
    
    ids = request.GET.get('ids', '').split(',')
    campaigns = Campaign.objects.filter(id__in=ids)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        if not rejection_reason:
            messages.error(request, 'Veuillez fournir une raison de rejet.')
        else:
            updated = 0
            for campaign in campaigns:
                if campaign.status == 'pending':
                    campaign.status = 'rejected'
                    campaign.approved_by = request.user
                    campaign.approved_at = timezone.now()
                    campaign.rejection_reason = rejection_reason
                    campaign.save()
                    updated += 1
            
            if updated > 0:
                messages.success(request, f'{updated} campagne(s) rejetée(s) avec succès.')
            else:
                messages.warning(request, "Aucune campagne n'a été rejetée. Vérifiez que les campagnes sont en attente.")
            
            return redirect('admin:spot_campaign_changelist')
    
    return render(request, 'spot/admin_reject_form.html', {
        'title': 'Rejeter les campagnes',
        'items': campaigns,
        'item_type': 'campagne'
    })

@login_required
def admin_spot_reject(request):
    """Vue pour rejeter des spots depuis l'admin avec une raison"""
    if not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('admin:index')
    
    ids = request.GET.get('ids', '').split(',')
    spots = Spot.objects.filter(id__in=ids)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        if not rejection_reason:
            messages.error(request, 'Veuillez fournir une raison de rejet.')
        else:
            updated = 0
            for spot in spots:
                if spot.status == 'pending':
                    spot.status = 'rejected'
                    spot.approved_by = request.user
                    spot.approved_at = timezone.now()
                    spot.rejection_reason = rejection_reason
                    spot.save()
                    updated += 1
            
            if updated > 0:
                messages.success(request, f'{updated} spot(s) rejeté(s) avec succès.')
            else:
                messages.warning(request, "Aucun spot n'a été rejeté. Vérifiez que les spots sont en attente.")
            
            return redirect('admin:spot_spot_changelist')
    
    return render(request, 'spot/admin_reject_form.html', {
        'title': 'Rejeter les spots',
        'items': spots,
        'item_type': 'spot'
    })
