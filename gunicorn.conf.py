# Configuration Gunicorn pour BF1 TV

import multiprocessing
import os

# Nom du module WSGI
wsgi_module = "spot_bf1.wsgi:application"

# Nombre de workers
workers = multiprocessing.cpu_count() * 2 + 1

# Nombre de threads par worker
threads = 2

# Adresse et port
bind = "0.0.0.0:8000"

# Timeout
timeout = 30
keepalive = 2

# Logging
# Use environment variables or default to local 'logs' directory
log_dir = os.environ.get('LOG_DIR', 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except:
        pass

accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
loglevel = "info"

# Processus
daemon = False
# pidfile = "/var/run/bf1tv/gunicorn.pid" # Commented out for portability
pidfile = "gunicorn.pid"

# User/Group - Commented out for cross-platform compatibility
# user = "www-data"
# group = "www-data"

# Préchargement
preload_app = True

# Variables d'environnement
raw_env = [
    'DJANGO_SETTINGS_MODULE=spot_bf1.settings_production',
]

# Configuration SSL (si nécessaire)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Configuration des workers
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Configuration de la mémoire
# worker_tmp_dir = "/dev/shm" # Linux specific

# Configuration des logs
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Configuration de sécurité
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
