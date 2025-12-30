from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from spot.models import TimeSlot, PricingRule

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialise les données de base pour BF1 TV'

    def handle(self, *args, **options):
        self.stdout.write('Initialisation des données de base...')
        
        # Créer un superutilisateur admin
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@bf1tv.bf',
                password='admin123',
                role='admin',
                phone='+226 XX XX XX XX',
                company='BF1 TV',
                address='Ouagadougou, Burkina Faso'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Superutilisateur admin créé avec succès')
            )
        else:
            self.stdout.write('Superutilisateur admin existe déjà')

        # Créer les créneaux horaires
        time_slots_data = [
            {
                'name': 'Heure creuse (Nuit)',
                'start_time': '00:00',
                'end_time': '06:00',
                'price_multiplier': 0.7,
                'description': 'Créneau nocturne avec audience réduite'
            },
            {
                'name': 'Matin (Petit-déjeuner)',
                'start_time': '06:00',
                'end_time': '09:00',
                'price_multiplier': 1.2,
                'description': 'Créneau matinal avec audience modérée'
            },
            {
                'name': 'Midi (Déjeuner)',
                'start_time': '12:00',
                'end_time': '14:00',
                'price_multiplier': 1.8,
                'description': 'Créneau de pointe du midi'
            },
            {
                'name': 'Après-midi',
                'start_time': '14:00',
                'end_time': '18:00',
                'price_multiplier': 1.0,
                'description': 'Créneau standard de l\'après-midi'
            },
            {
                'name': 'Soirée (Fin de journée)',
                'start_time': '18:00',
                'end_time': '19:00',
                'price_multiplier': 1.8,
                'description': 'Créneau de pointe du soir'
            },
            {
                'name': 'Prime Time',
                'start_time': '19:00',
                'end_time': '22:00',
                'price_multiplier': 2.5,
                'description': 'Créneau premium avec audience maximale'
            },
            {
                'name': 'Soirée tardive',
                'start_time': '22:00',
                'end_time': '00:00',
                'price_multiplier': 1.5,
                'description': 'Créneau de soirée avec audience modérée'
            }
        ]

        for slot_data in time_slots_data:
            time_slot, created = TimeSlot.objects.get_or_create(
                name=slot_data['name'],
                defaults=slot_data
            )
            if created:
                self.stdout.write(f'Créneau horaire créé: {time_slot.name}')
            else:
                self.stdout.write(f'Créneau horaire existe déjà: {time_slot.name}')

        # Créer les règles de tarification
        pricing_rules_data = [
            {
                'name': 'Spot court (5-15s)',
                'base_price': 800,
                'duration_min': 5,
                'duration_max': 15,
                'time_slot_multiplier': 1.0
            },
            {
                'name': 'Spot moyen (16-30s)',
                'base_price': 1000,
                'duration_min': 16,
                'duration_max': 30,
                'time_slot_multiplier': 1.0
            },
            {
                'name': 'Spot long (31-60s)',
                'base_price': 1200,
                'duration_min': 31,
                'duration_max': 60,
                'time_slot_multiplier': 1.0
            },
            {
                'name': 'Spot très long (61-120s)',
                'base_price': 1500,
                'duration_min': 61,
                'duration_max': 120,
                'time_slot_multiplier': 1.0
            },
            {
                'name': 'Spot documentaire (121-300s)',
                'base_price': 2000,
                'duration_min': 121,
                'duration_max': 300,
                'time_slot_multiplier': 1.0
            }
        ]

        for rule_data in pricing_rules_data:
            pricing_rule, created = PricingRule.objects.get_or_create(
                name=rule_data['name'],
                defaults=rule_data
            )
            if created:
                self.stdout.write(f'Règle de tarification créée: {pricing_rule.name}')
            else:
                self.stdout.write(f'Règle de tarification existe déjà: {pricing_rule.name}')

        self.stdout.write(
            self.style.SUCCESS('Initialisation des données terminée avec succès!')
        )
        self.stdout.write('\nInformations de connexion:')
        self.stdout.write('Utilisateur: admin')
        self.stdout.write('Mot de passe: admin123')
        self.stdout.write('URL: http://localhost:8000/admin/')
