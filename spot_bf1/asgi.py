"""
ASGI config for spot_bf1 project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spot_bf1.settings')

django_app = get_asgi_application()

_enable_channels = os.environ.get('ENABLE_CHANNELS', '0').strip().lower() in {'1', 'true', 'yes', 'on'}

if _enable_channels:
    try:
        from channels.routing import ProtocolTypeRouter, URLRouter
        from channels.auth import AuthMiddlewareStack
        import spot.routing

        application = ProtocolTypeRouter({
            'http': django_app,
            'websocket': AuthMiddlewareStack(
                URLRouter(
                    spot.routing.websocket_urlpatterns
                )
            ),
        })
    except Exception:
        application = django_app
else:
    application = django_app
