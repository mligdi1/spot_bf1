import os
import re
import json
from typing import List, Dict
from django.conf import settings


KB_DIR = getattr(settings, 'CHATBOT_KNOWLEDGE_DIR', os.path.join(settings.BASE_DIR, 'media', 'chatbot_kb'))
KB_INDEX_PATH = os.path.join(settings.BASE_DIR, 'media', 'chatbot_index.json')


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", (text or '').lower())


def build_index() -> Dict[str, Dict]:
    index: Dict[str, Dict] = {
        'docs': [],
        'vocab': {},
    }
    if not os.path.isdir(KB_DIR):
        os.makedirs(KB_DIR, exist_ok=True)
    for name in os.listdir(KB_DIR):
        if not name.lower().endswith(('.md', '.txt', '.json')):
            continue
        path = os.path.join(KB_DIR, name)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue
        tokens = _tokenize(content)
        doc = {
            'id': name,
            'title': name,
            'tokens': tokens,
            'length': len(tokens),
        }
        index['docs'].append(doc)
        for tok in tokens:
            index['vocab'][tok] = index['vocab'].get(tok, 0) + 1
    try:
        os.makedirs(os.path.dirname(KB_INDEX_PATH), exist_ok=True)
        with open(KB_INDEX_PATH, 'w', encoding='utf-8') as f:
            json.dump(index, f)
    except Exception:
        pass
    return index


def load_index() -> Dict[str, Dict]:
    try:
        with open(KB_INDEX_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'docs': [], 'vocab': {}}


def search(query: str, k: int = 3) -> List[Dict]:
    idx = load_index()
    q_tokens = _tokenize(query)
    scores: List[tuple] = []
    for doc in idx.get('docs', []):
        dtoks = set(doc.get('tokens', []))
        overlap = len(dtoks.intersection(q_tokens))
        scores.append((overlap, doc))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [doc for score, doc in scores[:k] if score > 0]