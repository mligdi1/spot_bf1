#!/bin/sh

# Script de démarrage pour BF1 TV
# Usage: ./start.sh [development|production]

set -e

# Configuration
ENVIRONMENT=${1:-development}
PROJECT_DIR="${PROJECT_DIR:-/app}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"

echo "🚀 Démarrage de BF1 TV - Environnement: $ENVIRONMENT"
echo "=================================================="

# Créer les répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p $LOG_DIR
mkdir -p $PROJECT_DIR/media
mkdir -p $PROJECT_DIR/staticfiles

# Activer l'environnement virtuel (si présent)
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "🐍 Activation de l'environnement virtuel..."
    . "$VENV_DIR/bin/activate"
fi

# Aller dans le répertoire du projet
cd $PROJECT_DIR

# Installer/mettre à jour les dépendances (optionnel)
if [ "${INSTALL_REQUIREMENTS:-0}" = "1" ]; then
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
fi

# Appliquer les migrations
echo "🗄️  Application des migrations..."
python manage.py migrate

# Collecter les fichiers statiques
echo "📄 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Initialiser les données si nécessaire
if [ "$ENVIRONMENT" = "development" ]; then
    echo "🔧 Initialisation des données de développement..."
    python manage.py init_data
fi

# Démarrer l'application
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🏭 Démarrage en mode production avec Gunicorn..."
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-spot_bf1.settings_production}"
    gunicorn -c gunicorn.conf.py spot_bf1.wsgi:application
else
    echo "🛠️  Démarrage en mode développement..."
    export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-spot_bf1.settings}"
    python manage.py runserver 0.0.0.0:8000
fi
