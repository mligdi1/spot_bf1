from typing import List, Dict, Optional, Any, Iterable, Tuple
from django.urls import reverse


INTENTS = {
    'admin_console': [
        'console',
        'admin',
        'approbation',
        'approuver',
        'valider',
        'rejeter',
        'demandes de couverture',
        'demandes de contact',
    ],
    'editorial': [
        'rédaction',
        'editorial',
        'journaliste',
        'journalistes',
        'chauffeur',
        'chauffeurs',
        'assignation',
        'assignations',
        'couvertures',
        'planning rédaction',
    ],
    'diffusion_space': [
        'diffuseur',
        'diffusion',
        'planning diffusion',
        'spots à diffuser',
        'spots diffusés',
        'spots en retard',
        'retards',
    ],
    'coverage_request': [
        'demande de couverture',
        'couverture médiatique',
        'couverture',
        'reportage',
        'événement',
        'evenement',
        'interview',
        'live',
        'presse',
    ],
    'create_campaign': ['créer une campagne', 'nouvelle campagne', 'campagne'],
    'upload_spot': ['téléverser un spot', 'televerser un spot', 'upload spot', 'upload', 'téléverse', 'televerse', 'spot'],
    'view_broadcasts': ['calendrier', 'planifier', 'diffusions', 'grille de diffusion'],
    'support': ['support', 'aide', 'humain', 'agent', 'contact', 'correspondence', 'discussion', 'ticket', 'tickets'],
    'pricing': ['tarif', 'tarifs', 'prix', 'coût', 'cout', 'simulateur'],
    'advisory': ['orientation', 'conseil', 'conseils', 'guide', 'guides', 'inspiration'],
    'reports': ['rapport', 'rapports', 'bilan', 'report', 'kpi', 'export', 'pdf', 'excel'],
    'notifications': ['notifications', 'notification', 'alertes', 'alerte'],
    'profile': ['profil', 'mon profil', 'compte', 'mot de passe'],
    'follow_threads': ['suivre mes échanges', 'suivre mes echanges', 'mes discussions', 'correspondance', 'threads'],
}


def _contains(text: str, phrases: List[str]) -> bool:
    t = (text or '').lower()
    return any(p in t for p in phrases)


def detect_intent(text: str) -> Optional[str]:
    t = (text or '').lower()
    if not t.strip():
        return None

    def score(phrases: Iterable[str]) -> int:
        s = 0
        for p in phrases:
            p2 = (p or '').lower().strip()
            if not p2:
                continue
            if p2 in t:
                s += max(1, len(p2) // 6)
        return s

    ranked: List[Tuple[int, int, str]] = []
    priority = [
        'admin_console',
        'editorial',
        'diffusion_space',
        'coverage_request',
        'support',
        'follow_threads',
        'pricing',
        'reports',
        'advisory',
        'notifications',
        'profile',
        'create_campaign',
        'upload_spot',
        'view_broadcasts',
    ]
    prio_index = {name: i for i, name in enumerate(priority)}

    for name, phrases in INTENTS.items():
        s = score(phrases)
        if s <= 0:
            continue
        ranked.append((s, -prio_index.get(name, 10_000), name))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][2]
    return None


def build_actions(intent: Optional[str], user: Optional[Any] = None) -> List[Dict[str, str]]:
    def link(name: str) -> str:
        try:
            return reverse(name)
        except Exception:
            return '#'

    is_admin = bool(user and getattr(user, 'is_admin', lambda: False)())
    is_editorial = bool(user and getattr(user, 'is_editorial_manager', lambda: False)())
    is_diffuser = bool(user and getattr(user, 'is_diffuser', lambda: False)())

    if not is_admin and intent == 'admin_console':
        intent = 'support'
    if not is_editorial and intent == 'editorial':
        intent = 'coverage_request'
    if not is_diffuser and intent == 'diffusion_space':
        intent = 'view_broadcasts'

    if is_admin:
        if intent in {'coverage_request', 'editorial'}:
            return [
                {'type': 'redirect', 'url': link('admin_coverage_list'), 'label': 'Demandes de couverture'},
                {'type': 'redirect', 'url': link('admin_dashboard'), 'label': 'Console admin'},
            ]
        if intent in {'support', 'follow_threads'}:
            return [
                {'type': 'redirect', 'url': link('correspondence_list'), 'label': 'Correspondance'},
                {'type': 'redirect', 'url': link('admin_dashboard'), 'label': 'Console admin'},
            ]
        if intent in {'create_campaign', 'upload_spot', 'view_broadcasts', 'diffusion_space'}:
            return [
                {'type': 'redirect', 'url': link('admin_campaign_list'), 'label': 'Campagnes (console)'},
                {'type': 'redirect', 'url': link('admin_dashboard'), 'label': 'Console admin'},
            ]
        return [
            {'type': 'redirect', 'url': link('admin_dashboard'), 'label': 'Console admin'},
            {'type': 'redirect', 'url': link('admin_campaign_list'), 'label': 'Campagnes (console)'},
            {'type': 'redirect', 'url': link('admin_coverage_list'), 'label': 'Demandes de couverture'},
        ]

    if is_editorial:
        if intent in {'editorial', 'coverage_request'}:
            return [
                {'type': 'redirect', 'url': link('editorial_dashboard'), 'label': 'Dashboard Rédaction'},
                {'type': 'redirect', 'url': link('editorial_coverages'), 'label': 'Demandes validées'},
                {'type': 'redirect', 'url': link('editorial_planning'), 'label': 'Planning'},
                {'type': 'redirect', 'url': link('editorial_assignments'), 'label': 'Assignations'},
            ]
        if intent == 'notifications':
            return [
                {'type': 'redirect', 'url': link('editorial_notifications'), 'label': 'Notifications Rédaction'},
                {'type': 'redirect', 'url': link('editorial_dashboard'), 'label': 'Dashboard Rédaction'},
            ]
        return [
            {'type': 'redirect', 'url': link('editorial_dashboard'), 'label': 'Dashboard Rédaction'},
            {'type': 'redirect', 'url': link('editorial_coverages'), 'label': 'Demandes validées'},
            {'type': 'redirect', 'url': link('editorial_journalists'), 'label': 'Journalistes'},
            {'type': 'redirect', 'url': link('editorial_drivers'), 'label': 'Chauffeurs'},
        ]

    if is_diffuser:
        if intent in {'diffusion_space', 'view_broadcasts'}:
            return [
                {'type': 'redirect', 'url': link('diffusion_home'), 'label': 'Accueil Diffusion'},
                {'type': 'redirect', 'url': link('diffusion_spots'), 'label': 'Spots'},
                {'type': 'redirect', 'url': link('diffusion_planning'), 'label': 'Planning'},
                {'type': 'redirect', 'url': link('diffusion_spots_late'), 'label': 'Spots en retard'},
            ]
        if intent == 'notifications':
            return [
                {'type': 'redirect', 'url': link('diffusion_notifications'), 'label': 'Notifications'},
                {'type': 'redirect', 'url': link('diffusion_home'), 'label': 'Accueil Diffusion'},
            ]
        if intent == 'profile':
            return [
                {'type': 'redirect', 'url': link('diffusion_profile'), 'label': 'Mon profil (Diffusion)'},
                {'type': 'redirect', 'url': link('diffusion_home'), 'label': 'Accueil Diffusion'},
            ]
        return [
            {'type': 'redirect', 'url': link('diffusion_home'), 'label': 'Accueil Diffusion'},
            {'type': 'redirect', 'url': link('diffusion_spots'), 'label': 'Spots'},
            {'type': 'redirect', 'url': link('diffusion_planning'), 'label': 'Planning'},
        ]

    if intent == 'create_campaign':
        return [
            {'type': 'redirect', 'url': link('campaign_spot_create'), 'label': 'Créer une campagne'},
            {'type': 'redirect', 'url': link('campaign_list'), 'label': 'Voir les campagnes'},
        ]
    if intent == 'upload_spot':
        # Redirection vers la liste des campagnes (sélection) avant upload
        return [
            {'type': 'redirect', 'url': link('campaign_list'), 'label': 'Téléverser un spot (choisir la campagne)'},
        ]
    if intent == 'view_broadcasts':
        return [
            {'type': 'redirect', 'url': link('broadcast_grid'), 'label': 'Voir mes diffusions'},
        ]
    if intent == 'coverage_request':
        return [
            {'type': 'redirect', 'url': link('coverage_request_create'), 'label': 'Faire une demande de couverture'},
        ]
    if intent == 'support':
        return [
            {'type': 'redirect', 'url': link('contact_advisor'), 'label': 'Parler à un agent humain'},
            {'type': 'redirect', 'url': link('correspondence_list'), 'label': 'Suivre mes échanges'},
            {'type': 'redirect', 'url': link('correspondence_new'), 'label': 'Créer une nouvelle discussion'},
        ]
    if intent == 'pricing':
        return [
            {'type': 'redirect', 'url': link('pricing_overview'), 'label': 'Voir les tarifs'},
            {'type': 'redirect', 'url': link('cost_simulator'), 'label': 'Simuler un coût'},
        ]
    if intent == 'advisory':
        return [
            {'type': 'redirect', 'url': link('advisory_wizard'), 'label': 'Orientation (assistant)'},
            {'type': 'redirect', 'url': link('guides_list'), 'label': 'Guides'},
            {'type': 'redirect', 'url': link('inspiration'), 'label': 'Inspiration'},
        ]
    if intent == 'reports':
        return [
            {'type': 'redirect', 'url': link('report_overview'), 'label': 'Bilan / Rapports'},
            {'type': 'redirect', 'url': link('report_export'), 'label': 'Exporter (Excel)'},
            {'type': 'redirect', 'url': link('report_export_pdf'), 'label': 'Exporter (PDF)'},
        ]
    if intent == 'notifications':
        return [
            {'type': 'redirect', 'url': link('notifications'), 'label': 'Mes notifications'},
        ]
    if intent == 'profile':
        return [
            {'type': 'redirect', 'url': link('profile'), 'label': 'Mon profil'},
        ]
    if intent == 'follow_threads':
        return [
            {'type': 'redirect', 'url': link('correspondence_list'), 'label': 'Suivre mes échanges'},
        ]
    # Par défaut: proposer les principales actions
    return [
        {'type': 'redirect', 'url': link('campaign_spot_create'), 'label': 'Créer une campagne'},
        {'type': 'redirect', 'url': link('campaign_list'), 'label': 'Voir mes campagnes'},
        {'type': 'redirect', 'url': link('broadcast_grid'), 'label': 'Voir mes diffusions'},
        {'type': 'redirect', 'url': link('coverage_request_create'), 'label': 'Demande de couverture'},
    ]


def guide_message(intent: Optional[str], user: Optional[Any] = None) -> str:
    is_admin = bool(user and getattr(user, 'is_admin', lambda: False)())
    is_editorial = bool(user and getattr(user, 'is_editorial_manager', lambda: False)())
    is_diffuser = bool(user and getattr(user, 'is_diffuser', lambda: False)())

    if not is_admin and intent == 'admin_console':
        intent = 'support'
    if not is_editorial and intent == 'editorial':
        intent = 'coverage_request'
    if not is_diffuser and intent == 'diffusion_space':
        intent = 'view_broadcasts'

    if is_admin:
        if intent in {'coverage_request', 'editorial'}:
            return "Console admin: consultez les demandes de couverture et mettez leur statut à jour."
        if intent in {'create_campaign', 'upload_spot'}:
            return "Console admin: vous pouvez approuver/rejeter les campagnes et les spots."
        return "Console admin: je peux vous orienter vers les écrans de gestion."

    if is_editorial:
        if intent in {'editorial', 'coverage_request'}:
            return "Rédaction: consultez les demandes validées, assignez une équipe et suivez le planning."
        return "Rédaction: je peux vous guider vers les couvertures, le planning, ou la gestion des équipes."

    if is_diffuser:
        if intent in {'diffusion_space', 'view_broadcasts'}:
            return "Diffusion: ouvrez le planning, filtrez par date/statut, et gérez les spots en retard."
        return "Diffusion: je peux vous guider vers les spots, le planning, et les notifications."

    if intent == 'create_campaign':
        return (
            "Pour créer une campagne: 1) renseignez le formulaire (objectif, budget, dates), "
            "2) validez, 3) téléversez votre spot si nécessaire."
        )
    if intent == 'upload_spot':
        return (
            "Pour téléverser un spot: choisissez d’abord la campagne, puis utilisez l’interface d’upload."
        )
    if intent == 'view_broadcasts':
        return (
            "Consultez vos diffusions dans la grille: filtrez par date et statut, et planifiez vos créneaux."
        )
    if intent == 'coverage_request':
        return "Demande de couverture: remplissez le formulaire (événement, date, contacts) puis validez."
    if intent == 'support':
        return (
            "Support: choisissez parler à un humain, suivre vos échanges, ou ouvrir une nouvelle discussion."
        )
    if intent == 'pricing':
        return (
            "Tarifs: comparez les options et utilisez le simulateur pour estimer le coût total."
        )
    if intent == 'advisory':
        return "Orientation: je peux vous guider avec l’assistant, les guides, et l’inspiration."
    if intent == 'reports':
        return "Bilan: ouvrez l’aperçu et utilisez les exports Excel/PDF si besoin."
    if intent == 'notifications':
        return "Notifications: consultez les dernières alertes et marquez-les comme lues."
    if intent == 'profile':
        return "Profil: mettez à jour vos informations et votre mot de passe."
    if intent == 'follow_threads':
        return (
            "Vos échanges: accédez à la page Correspondence pour consulter vos discussions et leur statut."
        )
    return (
        "Je peux vous guider sur les actions clés: campagnes, spots, diffusions, couverture, support."
    )
