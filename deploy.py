#!/usr/bin/env python3
"""
Script de déploiement pour BF1 TV
Usage: python deploy.py [production|staging|development]
"""

import os
import sys
import subprocess
import django
from pathlib import Path

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spot_bf1.settings')
django.setup()

def run_command(command, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Succès")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Erreur")
        print(f"Code de sortie: {e.returncode}")
        if e.stdout:
            print(f"Sortie: {e.stdout}")
        if e.stderr:
            print(f"Erreur: {e.stderr}")
        return False

def check_requirements():
    """Vérifie que tous les prérequis sont installés"""
    print("🔍 Vérification des prérequis...")
    
    # Vérifier Python
    python_version = sys.version_info
    if python_version < (3, 8):
        print("❌ Python 3.8+ requis")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Vérifier pip
    try:
        import pip
        print("✅ pip installé")
    except ImportError:
        print("❌ pip non installé")
        return False
    
    return True

def install_dependencies():
    """Installe les dépendances Python"""
    return run_command("pip install -r requirements.txt", "Installation des dépendances")

def setup_database():
    """Configure la base de données"""
    commands = [
        ("python manage.py makemigrations", "Création des migrations"),
        ("python manage.py migrate", "Application des migrations"),
        ("python manage.py init_data", "Initialisation des données de base")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def collect_static_files():
    """Collecte les fichiers statiques"""
    return run_command("python manage.py collectstatic --noinput", "Collecte des fichiers statiques")

def run_tests():
    """Lance les tests"""
    return run_command("python manage.py test", "Exécution des tests")

def create_directories():
    """Crée les répertoires nécessaires"""
    directories = ['media', 'staticfiles', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Répertoire créé: {directory}")

def main():
    """Fonction principale de déploiement"""
    print("🚀 Déploiement BF1 TV - Application de Gestion Publicitaire")
    print("=" * 60)
    
    # Vérifier les arguments
    environment = sys.argv[1] if len(sys.argv) > 1 else 'development'
    print(f"🌍 Environnement: {environment}")
    
    # Vérifier les prérequis
    if not check_requirements():
        print("❌ Prérequis non satisfaits")
        sys.exit(1)
    
    # Créer les répertoires
    create_directories()
    
    # Installer les dépendances
    if not install_dependencies():
        print("❌ Échec de l'installation des dépendances")
        sys.exit(1)
    
    # Configurer la base de données
    if not setup_database():
        print("❌ Échec de la configuration de la base de données")
        sys.exit(1)
    
    # Collecter les fichiers statiques
    if not collect_static_files():
        print("❌ Échec de la collecte des fichiers statiques")
        sys.exit(1)
    
    # Lancer les tests
    if not run_tests():
        print("❌ Échec des tests")
        sys.exit(1)
    
    print("\n🎉 Déploiement terminé avec succès!")
    print("\n📋 Informations de connexion:")
    print("   URL: http://localhost:8000")
    print("   Admin: http://localhost:8000/admin/")
    print("   Utilisateur: admin")
    print("   Mot de passe: admin123")
    
    print("\n🚀 Pour démarrer le serveur:")
    print("   python manage.py runserver")

if __name__ == "__main__":
    main()
