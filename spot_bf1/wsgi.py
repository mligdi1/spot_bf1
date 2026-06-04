"""
WSGI config for spot_bf1 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

# Détection automatique de l'environnement PythonAnywhere
path = os.path.expanduser('~')
if path.startswith('/home/spotbf1'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spot_bf1.settings_production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spot_bf1.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
