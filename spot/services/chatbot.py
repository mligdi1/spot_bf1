import os
import json
from typing import List, Dict, Optional
from django.conf import settings


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

    def reply(self, user_text: str, history: List[Dict[str, str]]) -> Dict[str, object]:
        t = (user_text or '').lower()
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
        if 'campagne' in t:
            return "Pour créer une campagne, ouvrez la page dédiée. Besoin d’une aide pas-à-pas ?"
        if 'spot' in t or 'upload' in t or 'télévers' in t:
            return "Vous pouvez téléverser votre spot depuis l’interface d’upload. Voulez-vous y aller ?"
        if 'diffus' in t or 'calendrier' in t or 'planifier' in t:
            return "La planification de diffusion se fait via le calendrier. Souhaitez-vous l’ouvrir ?"
        if 'contact' in t or 'humain' in t or 'support' in t:
            return "Je peux vous rediriger vers la page Contact pour parler à un humain."
        return "Je réfléchis à votre demande et je vous propose des options contextuelles."


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