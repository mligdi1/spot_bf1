import os
import json
from typing import List, Dict, Optional, Any
from django.conf import settings
from .nlu import detect_intent, build_actions


class ChatMemory:
    """
    Session-backed conversation memory.
    Stores last N turns (user/assistant) under the session key 'chatbot_history'.
    """
    SESSION_KEY = 'chatbot_history'

    def __init__(self, request):
        self.request = request
        self.max_len = getattr(settings, 'CHATBOT_MAX_CONTEXT', 8)

    def load(self) -> List[Dict[str, str]]:
        hist = self.request.session.get(self.SESSION_KEY, [])
        if not isinstance(hist, list):
            hist = []
        return hist[-self.max_len:]

    def append(self, role: str, content: str):
        hist = self.request.session.get(self.SESSION_KEY, [])
        hist.append({'role': role, 'content': content})
        self.request.session[self.SESSION_KEY] = hist[-self.max_len:]

    def clear(self):
        self.request.session[self.SESSION_KEY] = []


def _intent_actions(text: str) -> List[Dict[str, str]]:
    t = (text or '').lower()
    actions: List[Dict[str, str]] = []
    if 'campagne' in t:
        actions.append({'label': 'Créer une campagne', 'href': '/campaign/create/'})
        actions.append({'label': 'Voir mes campagnes', 'href': '/campaigns/'})
    if 'spot' in t or 'upload' in t or 'télévers' in t:
        actions.append({'label': 'Téléverser un spot', 'href': '/spot/upload/'})
        actions.append({'label': 'Voir mes spots', 'href': '/spots/'})
    if 'diffus' in t or 'calendrier' in t or 'planifier' in t:
        actions.append({'label': 'Voir mes diffusions', 'href': '/calendar/'})
    if 'contact' in t or 'humain' in t or 'support' in t:
        actions.append({'label': 'Parler à un humain', 'href': '/contact/'})
    return actions


def _load_kb_snippets() -> List[str]:
    kb_dir = getattr(settings, 'CHATBOT_KNOWLEDGE_DIR', '')
    out: List[str] = []
    if kb_dir and os.path.isdir(kb_dir):
        for name in os.listdir(kb_dir):
            if name.lower().endswith(('.txt', '.md')):
                p = os.path.join(kb_dir, name)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                        # Take first ~500 chars for context
                        out.append(f.read(1000))
                except Exception:
                    pass
    return out[:5]


class LocalLLMResponder:
    """
    Optional local LLM responder using llama.cpp or ctransformers if available.
    Falls back to rule-based responses when model or library is not present.
    Fully offline; never calls external services.
    """
    def __init__(self):
        self.model_path = getattr(settings, 'CHATBOT_MODEL_PATH', '')
        self.llm = None
        self._init_llm()

    def _init_llm(self):
        if not self.model_path:
            return
        # Try llama_cpp first
        try:
            from llama_cpp import Llama  # type: ignore
            self.llm = Llama(model_path=self.model_path, n_ctx=4096)
            return
        except Exception:
            self.llm = None
        # Try ctransformers as fallback
        if self.llm is None:
            try:
                from ctransformers import AutoModelForCausalLM  # type: ignore
                self.llm = AutoModelForCausalLM.from_pretrained(self.model_path, model_type='llama')
            except Exception:
                self.llm = None

    def _system_prompt(self) -> str:
        return (
            "Tu es Assistant BF1, un agent IA local, gratuit et autonome. "
            "Objectifs: répondre de façon intelligente et contextuelle, aider à résoudre des problèmes, "
            "assister l’apprentissage et la recherche, et proposer des suggestions personnalisées. "
            "Contraintes: aucune dépendance externe, aucune demande d’abonnement/paiement. "
            "Comporte-toi comme un assistant bienveillant, précis, et pratique, avec des étapes claires."
        )

    def _build_prompt(self, user_text: str, history: List[Dict[str, str]], kb: List[str]) -> str:
        lines = [f"System: {self._system_prompt()}"]
        if kb:
            lines.append("Connaissances locales:\n" + "\n---\n".join(kb))
        for item in history:
            role = item.get('role', 'user')
            content = item.get('content', '')
            lines.append(f"{role.capitalize()}: {content}")
        lines.append(f"User: {user_text}")
        lines.append("Assistant:")
        return "\n".join(lines)

    def _llm_reply(self, prompt: str) -> Optional[str]:
        if self.llm is None:
            return None
        try:
            # llama_cpp style
            if hasattr(self.llm, '__call__'):
                res = self.llm(prompt=prompt, max_tokens=256, temperature=0.6, stop=["User:"])
                txt = res.get('choices', [{}])[0].get('text', '')
                return (txt or '').strip()
            # ctransformers style
            if hasattr(self.llm, 'generate'):
                out = self.llm.generate(prompt, max_new_tokens=256, temperature=0.6)
                return (out or '').strip()
        except Exception:
            return None
        return None

    def reply(self, user_text: str, history: List[Dict[str, str]], user: Optional[Any] = None) -> Dict[str, object]:
        t = (user_text or '').lower()
        
        # 1. Détection d'intention via NLU
        intent = detect_intent(user_text)
        actions = build_actions(intent, user)
        
        # 2. Réponses détaillées selon l'intention
        if intent == 'bf1_tv':
            msg = (
                "### 📺 À propos de BF1 TV\n\n"
                "**BF1 TV** est une chaîne de télévision privée leader au Burkina Faso, reconnue pour son dynamisme et son professionnalisme. "
                "Elle se donne pour mission d'informer, d'éduquer et de divertir les populations à travers une programmation riche et variée.\n\n"
                "**Identité et Valeurs :**\n"
                "- **Proximité** : Être au plus près des préoccupations des Burkinabè.\n"
                "- **Innovation** : Utiliser les dernières technologies pour une diffusion de qualité.\n"
                "- **Professionnalisme** : Une équipe de journalistes et techniciens chevronnés.\n\n"
                "**Siège social :** Ouagadougou, Burkina Faso.\n\n"
                "Cette plateforme de gestion publicitaire est une extension de notre engagement à offrir des services modernes et accessibles à nos partenaires annonceurs."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'roles_permissions':
            msg = (
                "### 👥 Rôles et Permissions sur la Plateforme\n\n"
                "Le système est structuré autour de 4 profils principaux :\n\n"
                "1. **Client** : Peut créer des campagnes, téléverser des spots, suivre ses diffusions et demander des couvertures.\n"
                "2. **Administrateur** : Gère l'ensemble du système, valide les campagnes et les spots, et supervise les utilisateurs.\n"
                "3. **Responsable Rédaction** : Gère les demandes de couverture médiatique et assigne les équipes (journalistes/chauffeurs).\n"
                "4. **Diffuseur** : Accède à l'interface technique pour confirmer la diffusion réelle des spots à l'antenne.\n\n"
                "Chaque rôle dispose d'un tableau de bord personnalisé adapté à ses missions."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'technical_info':
            msg = (
                "### 💻 Informations Techniques\n\n"
                "Ce projet a été développé par **Nana Wend Kouni Marcel**.\n\n"
                "Les technologies utilisées pour construire cette plateforme sont principalement :\n"
                "- **Python** avec le framework **Django** pour le backend.\n"
                "- **JavaScript** avec **Tailwind CSS** et **Alpine.js** pour l'interface utilisateur.\n\n"
                "C'est une stack moderne choisie pour sa robustesse, sa sécurité et sa rapidité de développement."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'campaign_process':
            msg = (
                "### 🔄 Processus de Campagne\n\n"
                "Voici le cycle de vie d'une campagne sur notre plateforme :\n\n"
                "1. **Brouillon** : Vous préparez votre demande.\n"
                "2. **En attente** : Vous soumettez la campagne pour validation par l'admin.\n"
                "3. **Approuvée/Rejetée** : L'administration examine le budget et les objectifs.\n"
                "4. **Upload du Spot** : Une fois la campagne approuvée, vous fournissez le média.\n"
                "5. **Programmation** : Le spot est placé dans la grille de diffusion.\n"
                "6. **Diffusion** : Le spot passe à l'antenne et est marqué comme diffusé."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'ad_types':
            msg = (
                "### 🎞️ Types et Formats Publicitaires\n\n"
                "Nous acceptons deux formats principaux :\n\n"
                "- **Vidéo** : Formats MP4, AVI, MOV ou WMV. La durée peut varier de 5 à 300 secondes.\n"
                "- **Image** : Pour les écrans urbains ou les bannières, formats JPEG ou PNG.\n\n"
                "**Options de création :**\n"
                "- **Spot fourni** : Vous téléversez votre propre fichier fini.\n"
                "- **Demande de création** : Notre équipe créative peut vous accompagner dans la réalisation de votre spot publicitaire."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'about_site':
            msg = (
                "### 📺 Bienvenue sur BF1 TV - Gestion Publicitaire\n\n"
                "Ce projet est une plateforme innovante conçue pour **moderniser et simplifier l'accès à la publicité télévisée** au Burkina Faso.\n\n"
                "**Objectifs principaux :**\n"
                "- **Pédagogie** : Accompagner les annonceurs, des PME aux grandes entreprises, dans leur stratégie de communication.\n"
                "- **Accessibilité** : Digitaliser le processus de réservation pour gagner en temps et en efficacité.\n"
                "- **Transparence** : Offrir une visibilité claire sur les tarifs, les créneaux et les diffusions.\n\n"
                "**Ce que vous pouvez faire ici :**\n"
                "- Consulter nos tarifs détaillés.\n"
                "- Créer et gérer vos campagnes de A à Z.\n"
                "- Suivre la diffusion de vos spots en temps réel.\n"
                "- Demander des couvertures médiatiques pour vos événements.\n\n"
                "Consultez notre [Guide d'utilisation](/guides/) pour plus de détails."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'create_campaign':
            msg = (
                "### 📢 Procédure de création de Campagne\n\n"
                "Pour lancer une campagne publicitaire sur BF1 TV, suivez ces étapes :\n\n"
                "1. **Accédez au formulaire** : Allez sur la page [Nouvelle campagne](/campaign/create/).\n"
                "2. **Saisissez les informations requises** :\n"
                "   - **Titre** : Un nom explicite pour votre campagne.\n"
                "   - **Description** : Le contexte et les objectifs visés.\n"
                "   - **Dates** : Période souhaitée (début et fin).\n"
                "   - **Budget** : Montant indicatif alloué.\n"
                "   - **Type** : Choisissez entre 'Fournir un spot' ou 'Demander une création'.\n"
                "   - **Cible & Message** : Audience visée et message clé.\n"
                "3. **Validation** : Une fois soumis, notre équipe admin étudiera votre demande.\n\n"
                "**Lien direct** : [Lancer ma campagne](/campaign/create/)"
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'coverage_request':
            msg = (
                "### 🎥 Procédure de Demande de Couverture Médiatique\n\n"
                "Vous souhaitez que BF1 TV couvre votre événement ? Voici comment procéder :\n\n"
                "1. **Formulaire de demande** : Rendez-vous sur [Demande de couverture](/coverage/request/).\n"
                "2. **Informations à fournir par défaut** :\n"
                "   - **Titre de l'événement** : Nom de la manifestation.\n"
                "   - **Type** : Reportage, Interview, Direct, etc.\n"
                "   - **Date et Heure** : Précisez quand l'événement aura lieu.\n"
                "   - **Lieu** : Localisation exacte.\n"
                "   - **Description** : Enjeux et déroulement de l'événement.\n"
                "   - **Contact** : Nom et téléphone du responsable sur place.\n"
                "3. **Suivi** : Vous recevrez une notification dès que la rédaction aura traité votre demande.\n\n"
                "**Lien direct** : [Demander une couverture](/coverage/request/)"
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'site_navigation':
            msg = (
                "### 🗺️ Guide de Navigation du Site\n\n"
                "Voici un aperçu de ce que vous trouverez sur chaque page :\n\n"
                "- **[Accueil](/home/)** : Tableau de bord général, statistiques rapides et accès aux outils.\n"
                "- **[Mes Campagnes](/campaigns/)** : Liste de toutes vos demandes, leurs statuts (En attente, Approuvé, etc.) et détails.\n"
                "- **[Mes Spots](/spots/)** : Gestion de vos fichiers médias (vidéos/images) téléchargés.\n"
                "- **[Planning de Diffusion](/broadcasts/)** : Calendrier interactif montrant quand vos spots passeront à l'antenne.\n"
                "- **[Tarifs & Services](/pricing/)** : Grille tarifaire détaillée et présentation des offres.\n"
                "- **[Mon Profil](/profile/)** : Gestion de vos informations personnelles et de votre entreprise.\n"
                "- **[Notifications](/notifications/)** : Alertes sur l'avancement de vos dossiers."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        if intent == 'functional_elements':
            msg = (
                "### 🛠️ Éléments Fonctionnels et Outils\n\n"
                "La plateforme met à votre disposition plusieurs outils puissants :\n\n"
                "1. **[Assistant Conseil](/advisory/wizard/)** : Un questionnaire interactif pour vous aider à choisir la meilleure stratégie publicitaire.\n"
                "2. **[Rapports & Bilans](/reports/overview/)** : Analysez les performances de vos diffusions avec des graphiques et exportez-les en PDF/Excel.\n"
                "3. **[Support Chatbot](/home/)** : Moi-même ! Je suis là pour répondre à vos questions 24h/24.\n"
                "4. **[Système de Tickets](/correspondence/)** : Pour des échanges directs avec nos conseillers."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        # Support/Correspondence override: act as guide, quick actions, minimal conversation
        if any(k in t for k in ['support', 'correspondence', 'discussion', 'humain', 'agent', 'contact']):
            actions = [
                {'label': 'Parler à un agent humain', 'href': '/contact/'},
                {'label': 'Suivre mes échanges', 'href': '/correspondence/'},
                {'label': 'Créer une nouvelle discussion', 'href': '/correspondence/new/'},
            ]
            msg = (
                "Je vous guide: choisissez une option pour contacter le support, "
                "suivre vos échanges, ou ouvrir une nouvelle discussion."
            )
            return {'ok': True, 'message': msg, 'actions': actions}

        kb = _load_kb_snippets()
        prompt = self._build_prompt(user_text, history, kb)
        content = self._llm_reply(prompt)
        actions = _intent_actions(user_text)
        if content:
            return {'ok': True, 'message': content, 'actions': actions}
        # Fallback rule-based when no model or error
        msg = self._rule_based(user_text)
        return {'ok': True, 'message': msg, 'actions': actions}

    def _rule_based(self, text: str) -> str:
        t = (text or '').lower()
        
        # Redétecter l'intent pour les réponses détaillées si le LLM échoue
        intent = detect_intent(text)
        
        # Mapping des réponses pour le mode dégradé (fallback)
        responses = {
            'bf1_tv': (
                "### 📺 À propos de BF1 TV\n\n"
                "BF1 TV est une chaîne privée leader au Burkina Faso, dédiée à l'information, l'éducation et le divertissement. "
                "Basée à Ouagadougou, elle mise sur le professionnalisme et l'innovation."
            ),
            'roles_permissions': (
                "### 👥 Rôles\n\n"
                "Le site gère 4 profils : Clients (vous), Administrateurs (gestion), Rédaction (couverture) et Diffuseurs (antenne)."
            ),
            'technical_info': (
                "### 💻 Technique\n\n"
                "Ce projet a été développé par **Nana Wend Kouni Marcel**. "
                "Stack: Python/Django, JS avec Tailwind. Sécurité et performance garanties."
            ),
            'campaign_process': (
                "### 🔄 Processus\n\n"
                "Étapes: Création → Validation Admin → Dépôt du spot → Programmation → Diffusion à l'antenne."
            ),
            'ad_types': (
                "### 🎞️ Formats\n\n"
                "Nous acceptons les Vidéos (MP4/AVI) et les Images (PNG/JPG). Durée des spots : 5 à 300 secondes."
            ),
            'about_site': (
                "### 📺 Bienvenue sur BF1 TV - Gestion Publicitaire\n\n"
                "Ce projet est une plateforme innovante conçue pour **moderniser et simplifier l'accès à la publicité télévisée** au Burkina Faso.\n\n"
                "Consultez notre [Guide d'utilisation](/guides/) pour plus de détails."
            ),
            'create_campaign': "Pour créer une campagne, rendez-vous sur la page [Nouvelle campagne](/campaign/create/). Vous devrez fournir un titre, une description, vos dates et votre budget.",
            'coverage_request': "Pour une demande de couverture médiatique, utilisez le formulaire [Demande de couverture](/coverage/request/).",
        }

        if intent in responses:
            return responses[intent]
        
        if 'campagne' in t:
            return "Pour créer une campagne, ouvrez la page dédiée. Besoin d’une aide pas-à-pas ?"
        if 'spot' in t:
            return "Vous pouvez téléverser vos spots dans l'onglet 'Mes Spots' une fois votre campagne approuvée."
        
        return "Je réfléchis à votre demande. Essayez des mots-clés comme 'BF1 TV', 'tarifs', 'campagne' ou 'processus' pour obtenir des informations précises."


def append_persistent_memory(text: str, reply: str):
    if not getattr(settings, 'CHATBOT_ENABLE_PERSISTENT_MEMORY', True):
        return
    path = getattr(settings, 'CHATBOT_MEMORY_PATH', '')
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'q': text, 'a': reply}) + "\n")
    except Exception:
        pass