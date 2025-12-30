import os
import json
from django.conf import settings


UNRESOLVED_LOG = os.path.join(settings.BASE_DIR, 'media', 'chatbot_unresolved.jsonl')


def log_unresolved(query: str, meta: dict = None):
    try:
        os.makedirs(os.path.dirname(UNRESOLVED_LOG), exist_ok=True)
        with open(UNRESOLVED_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'q': query, 'meta': meta or {}}) + "\n")
    except Exception:
        pass