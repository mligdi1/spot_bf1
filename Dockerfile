# Dockerfile pour BF1 TV
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=spot_bf1.settings

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gettext \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . /app/

# Création des répertoires nécessaires
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Collecte des fichiers statiques
RUN python manage.py collectstatic --noinput

# Exposer le port
EXPOSE 8000

# Script de démarrage
COPY start.sh /app/
RUN python -c "import pathlib; p = pathlib.Path('/app/start.sh'); p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n'))" \
    && chmod +x /app/start.sh

# Commande par défaut
CMD ["/app/start.sh", "production"]
