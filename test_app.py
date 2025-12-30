#!/usr/bin/env python3
"""
Script de test pour l'application BF1 TV
Vérifie que tous les composants fonctionnent correctement
"""

import os
import sys
import django
from pathlib import Path

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spot_bf1.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.management import call_command

User = get_user_model()


def test_database_connection():
    """Test de connexion à la base de données"""
    print("🔍 Test de connexion à la base de données...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        print("✅ Connexion à la base de données réussie")
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        return False


def test_models():
    """Test des modèles"""
    print("🔍 Test des modèles...")
    try:
        from spot.models import User, Campaign, Spot, Payment, TimeSlot, PricingRule
        
        # Test création utilisateur
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )
        print("✅ Modèle User fonctionne")
        
        # Test création campagne
        campaign = Campaign.objects.create(
            client=user,
            title='Test Campaign',
            description='Test Description',
            start_date='2024-01-01',
            end_date='2024-01-31',
            budget=100000
        )
        print("✅ Modèle Campaign fonctionne")
        
        # Test création spot
        spot = Spot.objects.create(
            campaign=campaign,
            title='Test Spot',
            duration_seconds=30
        )
        print("✅ Modèle Spot fonctionne")
        
        # Nettoyer les données de test
        spot.delete()
        campaign.delete()
        user.delete()
        
        return True
    except Exception as e:
        print(f"❌ Erreur dans les modèles: {e}")
        return False


def test_views():
    """Test des vues principales"""
    print("🔍 Test des vues...")
    try:
        client = Client()
        
        # Test page d'accueil
        response = client.get('/')
        if response.status_code == 200:
            print("✅ Page d'accueil accessible")
        else:
            print(f"❌ Erreur page d'accueil: {response.status_code}")
            return False
        
        # Test page de connexion
        response = client.get('/login/')
        if response.status_code == 200:
            print("✅ Page de connexion accessible")
        else:
            print(f"❌ Erreur page de connexion: {response.status_code}")
            return False
        
        # Test simulateur de coût
        response = client.get('/cost-simulator/')
        if response.status_code == 200:
            print("✅ Simulateur de coût accessible")
        else:
            print(f"❌ Erreur simulateur: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erreur dans les vues: {e}")
        return False


def test_authentication():
    """Test du système d'authentification"""
    print("🔍 Test de l'authentification...")
    try:
        client = Client()
        
        # Créer un utilisateur de test
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )
        
        # Test connexion
        response = client.post('/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        if response.status_code == 302:  # Redirection après connexion
            print("✅ Connexion utilisateur réussie")
        else:
            print(f"❌ Erreur de connexion: {response.status_code}")
            return False
        
        # Test accès au tableau de bord
        response = client.get('/dashboard/')
        if response.status_code == 200:
            print("✅ Accès au tableau de bord réussi")
        else:
            print(f"❌ Erreur accès tableau de bord: {response.status_code}")
            return False
        
        # Nettoyer
        user.delete()
        
        return True
    except Exception as e:
        print(f"❌ Erreur dans l'authentification: {e}")
        return False


def test_static_files():
    """Test des fichiers statiques"""
    print("🔍 Test des fichiers statiques...")
    try:
        from django.conf import settings
        
        # Vérifier que les répertoires existent
        static_dir = Path(settings.STATIC_ROOT)
        media_dir = Path(settings.MEDIA_ROOT)
        
        if static_dir.exists():
            print("✅ Répertoire static existe")
        else:
            print("❌ Répertoire static manquant")
            return False
        
        if media_dir.exists():
            print("✅ Répertoire media existe")
        else:
            print("❌ Répertoire media manquant")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erreur dans les fichiers statiques: {e}")
        return False


def test_admin_interface():
    """Test de l'interface d'administration"""
    print("🔍 Test de l'interface d'administration...")
    try:
        client = Client()
        
        # Test accès à l'admin
        response = client.get('/admin/')
        if response.status_code in [200, 302]:  # 302 si redirection vers login
            print("✅ Interface d'administration accessible")
        else:
            print(f"❌ Erreur interface admin: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erreur dans l'interface d'administration: {e}")
        return False


def run_django_tests():
    """Lance les tests Django"""
    print("🔍 Lancement des tests Django...")
    try:
        call_command('test', verbosity=0)
        print("✅ Tous les tests Django passent")
        return True
    except Exception as e:
        print(f"❌ Erreur dans les tests Django: {e}")
        return False


def main():
    """Fonction principale de test"""
    print("🧪 Test de l'application BF1 TV")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_models,
        test_views,
        test_authentication,
        test_static_files,
        test_admin_interface,
        run_django_tests,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Ligne vide entre les tests
        except Exception as e:
            print(f"❌ Erreur inattendue dans {test.__name__}: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés! L'application est prête.")
        return True
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
