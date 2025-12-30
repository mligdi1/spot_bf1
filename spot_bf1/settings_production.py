"""
Configuration de production pour BF1 TV
"""

from .settings import *
import os

# Sécurité
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# Base de données de production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'spot_bf1_prod'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
    }
}

if os.environ.get('DJANGO_USE_SQLITE') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Sécurité HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Cookies sécurisés
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Fichiers statiques et média
STATIC_ROOT = os.environ.get('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', str(BASE_DIR / 'media'))

# Email de production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@bf1tv.bf')

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# Channels (Redis si disponible, sinon fallback mémoire)
_redis_url = os.environ.get('REDIS_URL', '').strip()
_has_channels_redis = False
try:
    import channels_redis  # noqa: F401
    _has_channels_redis = True
except Exception:
    _has_channels_redis = False

if _redis_url and _has_channels_redis:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [_redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }

# Sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Logging path helper
def get_log_path(filename):
    log_dir = os.environ.get('LOG_DIR', str(BASE_DIR / 'logs'))
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            # Fallback to tmp if we can't write to logs
            import tempfile
            log_dir = tempfile.gettempdir()
    return os.path.join(log_dir, filename)

# Logging de production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': get_log_path('django.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': get_log_path('errors.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose'
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'spot': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Configuration du site
SITE_URL = os.environ.get('SITE_URL', 'https://bf1tv.bf')

# Mobile Money API (Production)
MOBILE_MONEY_API_URL = os.environ.get('MOBILE_MONEY_API_URL')
MOBILE_MONEY_API_KEY = os.environ.get('MOBILE_MONEY_API_KEY')
MOBILE_MONEY_MERCHANT_ID = os.environ.get('MOBILE_MONEY_MERCHANT_ID')

# WhatsApp Chat Widget (Production overrides)
WHATSAPP_PHONE = os.environ.get('WHATSAPP_PHONE', WHATSAPP_PHONE)
WHATSAPP_DEFAULT_MESSAGE = os.environ.get('WHATSAPP_DEFAULT_MESSAGE', WHATSAPP_DEFAULT_MESSAGE)
WHATSAPP_WIDGET_ENABLED = os.environ.get('WHATSAPP_WIDGET_ENABLED', str(WHATSAPP_WIDGET_ENABLED)).lower() in ('1','true','yes')
WHATSAPP_WIDGET_POSITION = os.environ.get('WHATSAPP_WIDGET_POSITION', WHATSAPP_WIDGET_POSITION)
WHATSAPP_WIDGET_COLOR = os.environ.get('WHATSAPP_WIDGET_COLOR', WHATSAPP_WIDGET_COLOR)
WHATSAPP_WIDGET_SIZE = os.environ.get('WHATSAPP_WIDGET_SIZE', WHATSAPP_WIDGET_SIZE)
