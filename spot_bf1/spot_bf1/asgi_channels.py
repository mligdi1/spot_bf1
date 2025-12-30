"""
ASGI config for spot_bf1 project (channels-first import order).
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spot_bf1.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Ensure Django apps are loaded before importing routing that touches models
django_app = get_asgi_application()

import spot.routing  # noqa: E402  (import after Django setup)

application = ProtocolTypeRouter({
    'http': django_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            spot.routing.websocket_urlpatterns
        )
    ),
})