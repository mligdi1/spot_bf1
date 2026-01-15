"""
Tests de charge avec Locust pour BF1 TV
Usage: locust -f locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between
import random
import os

class BF1TVUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Actions effectuées au démarrage de chaque utilisateur"""
        # Visiter la page d'accueil
        self.client.get("/")
    
    @task(3)
    def view_home_page(self):
        """Visiter la page d'accueil"""
        self.client.get("/")
    
    @task(2)
    def view_login_page(self):
        """Visiter la page de connexion"""
        self.client.get("/login/")
    
    @task(2)
    def view_register_page(self):
        """Visiter la page d'inscription"""
        self.client.get("/register/")
    
    @task(4)
    def use_cost_simulator(self):
        """Utiliser le simulateur de coût"""
        # Visiter la page du simulateur
        self.client.get("/cost-simulator/")
        
        # Simuler une utilisation du simulateur
        simulator_data = {
            'duration': random.randint(5, 300),
            'broadcast_count': random.randint(1, 100),
            'campaign_duration': random.randint(1, 365)
        }
        
        # Note: Dans un vrai test, il faudrait d'abord récupérer les créneaux horaires disponibles
        # Pour simplifier, on utilise un ID fictif
        simulator_data['time_slot'] = 1
        
        self.client.post("/cost-simulator/", data=simulator_data)
    
    @task(1)
    def view_admin_interface(self):
        """Visiter l'interface d'administration"""
        self.client.get("/admin/")
    
    @task(1)
    def view_static_files(self):
        """Télécharger des fichiers statiques"""
        static_files = [
            "/static/css/tailwind.css",
            "/static/js/app.js",
            "/favicon.ico"
        ]
        
        file_to_load = random.choice(static_files)
        self.client.get(file_to_load)


class AuthenticatedUser(HttpUser):
    wait_time = between(2, 5)
    
    def on_start(self):
        """Connexion de l'utilisateur"""
        # Visiter la page de connexion
        self.client.get("/login/")
        
        # Se connecter (avec des identifiants de test)
        login_data = {
            'username': 'testuser',
            'password': os.environ.get('LOCUST_TEST_PASSWORD', '')
        }
        
        response = self.client.post("/login/", data=login_data)
        
        if response.status_code == 302:  # Redirection après connexion
            self.client.get("/home/")
    
    @task(3)
    def view_home(self):
        self.client.get("/home/")
    
    @task(2)
    def view_campaigns(self):
        """Consulter les campagnes"""
        self.client.get("/campaigns/")
    
    @task(1)
    def create_campaign(self):
        """Créer une nouvelle campagne"""
        # Visiter la page de création
        self.client.get("/campaigns/create/")
        
        # Données de test pour une campagne
        campaign_data = {
            'title': f'Campagne de test {random.randint(1, 1000)}',
            'description': 'Description de test pour la campagne',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'budget': random.randint(10000, 1000000)
        }
        
        self.client.post("/campaigns/create/", data=campaign_data)
    
    @task(1)
    def view_notifications(self):
        """Consulter les notifications"""
        self.client.get("/notifications/")
    
    @task(1)
    def use_cost_simulator(self):
        """Utiliser le simulateur de coût"""
        self.client.get("/cost-simulator/")
        
        simulator_data = {
            'duration': random.randint(5, 300),
            'broadcast_count': random.randint(1, 100),
            'campaign_duration': random.randint(1, 365),
            'time_slot': 1
        }
        
        self.client.post("/cost-simulator/", data=simulator_data)


class AdminUser(HttpUser):
    wait_time = between(3, 7)
    
    def on_start(self):
        """Connexion de l'administrateur"""
        # Visiter la page de connexion
        self.client.get("/console/login/")
        
        # Se connecter en tant qu'admin
        login_data = {
            'username': 'admin',
            'password': os.environ.get('LOCUST_ADMIN_PASSWORD', '')
        }
        
        response = self.client.post("/console/login/", data=login_data)
        
        if response.status_code == 302:
            # Visiter le tableau de bord admin
            self.client.get("/console/dashboard/")
    
    @task(3)
    def view_admin_dashboard(self):
        """Consulter le tableau de bord administrateur"""
        self.client.get("/console/dashboard/")
    
    @task(2)
    def view_admin_interface(self):
        """Consulter l'interface d'administration Django"""
        self.client.get("/admin/")
    
    @task(1)
    def approve_campaigns(self):
        """Approuver des campagnes"""
        # Dans un vrai test, il faudrait d'abord récupérer les campagnes en attente
        # Pour simplifier, on utilise un ID fictif
        campaign_id = random.randint(1, 100)
        self.client.get(f"/admin/campaigns/{campaign_id}/approve/")
    
    @task(1)
    def approve_spots(self):
        """Approuver des spots"""
        spot_id = random.randint(1, 100)
        self.client.get(f"/admin/spots/{spot_id}/approve/")


# Configuration des scénarios de test
class WebsiteUser(BF1TVUser):
    weight = 70  # 70% des utilisateurs


class LoggedInUser(AuthenticatedUser):
    weight = 25  # 25% des utilisateurs


class AdminUser(AdminUser):
    weight = 5   # 5% des utilisateurs
