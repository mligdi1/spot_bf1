from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
import uuid

from .models import Campaign, Spot, TimeSlot, PricingRule
from .models import SpotSchedule, Notification, CorrespondenceThread
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date, datetime, timedelta, time
import urllib.parse

User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='testclient',
            email='client@test.com',
            password='testpass123',
            role='client',
            phone='+226 70 12 34 56',
            company='Test Company'
        )
        
        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )

    def test_client_creation(self):
        self.assertEqual(self.client_user.role, 'client')
        self.assertTrue(self.client_user.is_client())
        self.assertFalse(self.client_user.is_admin())

    def test_admin_creation(self):
        self.assertEqual(self.admin_user.role, 'admin')
        self.assertTrue(self.admin_user.is_admin())
        self.assertFalse(self.admin_user.is_client())


class CampaignModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )
        
        self.campaign = Campaign.objects.create(
            client=self.user,
            title='Test Campaign',
            description='Test Description',
            start_date='2024-01-01',
            end_date='2024-01-31',
            budget=Decimal('100000.00')
        )

    def test_campaign_creation(self):
        self.assertEqual(self.campaign.title, 'Test Campaign')
        self.assertEqual(self.campaign.client, self.user)
        self.assertEqual(self.campaign.status, 'draft')

    def test_campaign_duration(self):
        self.assertEqual(self.campaign.duration_days, 31)


class SpotModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )
        
        self.campaign = Campaign.objects.create(
            client=self.user,
            title='Test Campaign',
            description='Test Description',
            start_date='2024-01-01',
            end_date='2024-01-31',
            budget=Decimal('100000.00')
        )

    def test_spot_creation(self):
        spot = Spot.objects.create(
            campaign=self.campaign,
            title='Test Spot',
            description='Test Spot Description',
            duration_seconds=30
        )
        
        self.assertEqual(spot.title, 'Test Spot')
        self.assertEqual(spot.campaign, self.campaign)
        self.assertEqual(spot.status, 'uploaded')


class TimeSlotModelTest(TestCase):
    def setUp(self):
        self.time_slot = TimeSlot.objects.create(
            name='Prime Time',
            start_time='19:00',
            end_time='22:00',
            price_multiplier=Decimal('2.5'),
            description='Créneau premium'
        )

    def test_time_slot_creation(self):
        self.assertEqual(self.time_slot.name, 'Prime Time')
        self.assertEqual(self.time_slot.price_multiplier, Decimal('2.5'))


class PricingRuleModelTest(TestCase):
    def setUp(self):
        self.pricing_rule = PricingRule.objects.create(
            name='Spot moyen',
            base_price=Decimal('1000.00'),
            duration_min=16,
            duration_max=30,
            time_slot_multiplier=Decimal('1.0')
        )

    def test_pricing_rule_creation(self):
        self.assertEqual(self.pricing_rule.name, 'Spot moyen')
        self.assertEqual(self.pricing_rule.base_price, Decimal('1000.00'))


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BF1')

    def test_login_view(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connexion')

    def test_register_view(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Créer votre compte')

    def test_cost_simulator_view(self):
        response = self.client.get(reverse('cost_simulator'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('cost_simulator')}")

class DiffusionAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.diffuser = User.objects.create_user(username='diff', password='pass1234', role='diffuser')
        self.admin = User.objects.create_user(username='admin1', password='pass1234', role='admin')

    def test_diffuser_cannot_access_standard_views(self):
        self.client.login(username='diff', password='pass1234')
        blocked = [
            'home',
            'campaign_list',
            'campaign_create',
            'campaign_spot_create',
            'coverage_request_create',
            'spot_list',
            'broadcast_grid',
            'correspondence_list',
            'pricing_overview',
            'report_overview',
        ]
        for name in blocked:
            url = reverse(name)
            resp = self.client.get(url, follow=False)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp['Location'], reverse('diffusion_home'))

    def test_diffuser_can_access_diffusion_home(self):
        self.client.login(username='diff', password='pass1234')
        resp = self.client.get(reverse('diffusion_home'))
        self.assertEqual(resp.status_code, 200)

    def test_login_ignores_next_to_standard_view_for_diffuser(self):
        next_path = reverse('campaign_list')
        login_url = f"{reverse('login')}?next={urllib.parse.quote(next_path)}"
        resp = self.client.post(login_url, {'username': 'diff', 'password': 'pass1234'}, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('diffusion_home'))

    def test_diffuser_can_open_support_chat_and_notifies_admin_on_message(self):
        self.client.login(username='diff', password='pass1234')
        resp = self.client.get(reverse('diffusion_support_chat'), follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/diffusion/chat/', resp['Location'])

        thread_id = resp['Location'].rstrip('/').split('/')[-1]
        thread_url = reverse('diffusion_chat_thread', kwargs={'thread_id': thread_id})
        resp2 = self.client.get(thread_url)
        self.assertEqual(resp2.status_code, 200)

        resp3 = self.client.post(thread_url, {'content': 'Bonjour admin'}, follow=False)
        self.assertEqual(resp3.status_code, 302)
        self.assertTrue(Notification.objects.filter(user=self.admin, related_thread__isnull=False).exists())


class FormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )

    def test_campaign_form_valid(self):
        from .forms import CampaignForm
        start = timezone.localdate() + timedelta(days=1)
        end = start + timedelta(days=30)
        form_data = {
            'title': 'Test Campaign',
            'description': 'Test Description',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'budget': '100000',
            'campaign_type': 'spot_upload',
        }
        
        form = CampaignForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_campaign_form_invalid_dates(self):
        from .forms import CampaignForm
        end = timezone.localdate() + timedelta(days=1)
        start = end + timedelta(days=10)
        form_data = {
            'title': 'Test Campaign',
            'description': 'Test Description',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),  # Date de fin avant date de début
            'budget': '100000'
        }
        
        form = CampaignForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_register_username_is_case_insensitive(self):
        from .forms import CustomUserCreationForm
        User.objects.create_user(
            username='Nana',
            email='nana1@test.com',
            password='testpass123',
            role='client',
            phone='000',
            company='X'
        )
        form = CustomUserCreationForm(data={
            'username': 'nana',
            'email': 'nana2@test.com',
            'first_name': 'N',
            'last_name': 'A',
            'phone': '111',
            'company': 'Y',
            'address': '',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_login_username_is_case_insensitive(self):
        User.objects.create_user(
            username='Nana',
            email='nana3@test.com',
            password='testpass123',
            role='client',
            phone='000',
            company='X'
        )
        self.assertTrue(self.client.login(username='nana', password='testpass123'))


class IntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='client'
        )
        
        # Créer des données de test
        self.time_slot = TimeSlot.objects.create(
            name='Prime Time',
            start_time='19:00',
            end_time='22:00',
            price_multiplier=Decimal('2.5')
        )

    def test_complete_campaign_workflow(self):
        """Test du workflow complet d'une campagne"""
        # 1. Connexion
        self.client.login(username='testuser', password='testpass123')
        
        # 2. Création d'une campagne
        start = timezone.localdate() + timedelta(days=1)
        end = start + timedelta(days=30)
        campaign_data = {
            'title': 'Test Campaign',
            'description': 'Test Description',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'budget': '100000',
            'campaign_type': 'spot_upload',
        }
        
        response = self.client.post(reverse('campaign_create'), campaign_data)
        self.assertEqual(response.status_code, 302)  # Redirection après création
        
        # 3. Vérifier que la campagne a été créée
        campaign = Campaign.objects.get(title='Test Campaign')
        self.assertEqual(campaign.client, self.user)
        self.assertEqual(campaign.status, 'pending')

    def test_cost_simulator_calculation(self):
        """Test du simulateur de coût"""
        self.client.login(username='testuser', password='testpass123')
        
        simulator_data = {
            'duration': 30,
            'time_slot': self.time_slot.id,
            'broadcast_count': 10,
            'campaign_duration': 30
        }
        
        response = self.client.post(reverse('cost_simulator'), simulator_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coût estimé')


class AdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='adminpass123',
            role='admin'
        )
        
        self.client_user = User.objects.create_user(
            username='client',
            email='client@test.com',
            password='clientpass123',
            role='client'
        )

    def test_admin_dashboard_access(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_client_cannot_access_admin_dashboard(self):
        self.client.login(username='client', password='clientpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, reverse('home'))


class ReportExportFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='clientx', email='clientx@test.com', password='pass123', role='client'
        )
        self.client.login(username='clientx', password='pass123')

        self.time_slot = TimeSlot.objects.create(
            name='Matin',
            start_time=time(8, 0),
            end_time=time(9, 0),
            price_multiplier=Decimal('1.00'),
            is_active=True,
        )

        # Campagnes
        self.camp1 = Campaign.objects.create(
            client=self.user, title='Camp 1', description='Desc', start_date=date(2024, 2, 1), end_date=date(2024, 2, 28), budget=Decimal('50000')
        )
        self.camp2 = Campaign.objects.create(
            client=self.user, title='Camp 2', description='Desc', start_date=date(2024, 3, 1), end_date=date(2024, 3, 31), budget=Decimal('80000')
        )
        # Ajuster created_at pour le filtrage par mois
        Campaign.objects.filter(id=self.camp1.id).update(created_at=timezone.make_aware(datetime(2024, 2, 15)))
        Campaign.objects.filter(id=self.camp2.id).update(created_at=timezone.make_aware(datetime(2024, 3, 10)))
        self.camp1.refresh_from_db(); self.camp2.refresh_from_db()

        # Spots
        self.spot1 = Spot.objects.create(campaign=self.camp1, title='Spot 1', description='S1', duration_seconds=30)
        self.spot2 = Spot.objects.create(campaign=self.camp2, title='Spot 2', description='S2', duration_seconds=45)

        # Diffusions: une dans la période (février), une hors période (mars)
        self.sch_in = SpotSchedule.objects.create(
            spot=self.spot1,
            time_slot=self.time_slot,
            broadcast_date=date(2024, 2, 10),
            broadcast_time=time(8, 15),
            price=Decimal('1000.00'),
        )
        self.sch_out = SpotSchedule.objects.create(
            spot=self.spot2,
            time_slot=self.time_slot,
            broadcast_date=date(2024, 3, 5),
            broadcast_time=time(8, 30),
            price=Decimal('1200.00'),
        )

    def test_overview_filters_by_period(self):
        resp = self.client.get(reverse('report_overview'), {'start': '2024-02-01', 'end': '2024-02-28'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['campaigns_count'], 1)
        self.assertEqual(resp.context['campaigns_month'].count(), 1)
        self.assertEqual(resp.context['total_budget_month'], Decimal('50000'))

    def test_overview_inverted_dates_are_corrected(self):
        resp = self.client.get(reverse('report_overview'), {'start': '2024-02-28', 'end': '2024-02-01'})
        self.assertEqual(resp.status_code, 200)
        sd = resp.context['start_date']; ed = resp.context['end_date']
        self.assertLessEqual(sd, ed)
        self.assertEqual(resp.context['campaigns_count'], 1)

    def test_overview_invalid_formats_fallback_to_month(self):
        # Période invalide => retombe sur mois courant
        resp = self.client.get(reverse('report_overview'), {'start': 'xxx', 'end': 'yyy'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context['start_date'])
        self.assertIsNotNone(resp.context['end_date'])

    def test_overview_empty_params_default_current_month(self):
        # Crée une campagne dans le mois courant
        today = timezone.localdate()
        Campaign.objects.create(
            client=self.user,
            title='Current Camp',
            description='C',
            start_date=today,
            end_date=today + timedelta(days=1),
            budget=Decimal('1000'),
        )
        resp = self.client.get(reverse('report_overview'))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.context['campaigns_count'], 1)

    def test_pdf_export_respects_period_and_updates_history(self):
        resp = self.client.get(reverse('report_export_pdf'), {'start': '2024-02-01', 'end': '2024-02-28'})
        # PDF export: status 200 et content-type PDF
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp['Content-Type'].startswith('application/pdf'))
        # Historique de session mis à jour
        hist = self.client.session.get('export_history', [])
        self.assertGreaterEqual(len(hist), 1)
        self.assertEqual(hist[0]['format'], 'pdf')
        self.assertEqual(hist[0]['start'], '2024-02-01')
        self.assertEqual(hist[0]['end'], '2024-02-28')

    def test_excel_export_respects_period_or_redirects_if_missing_dep(self):
        resp = self.client.get(reverse('report_export'), {'start': '2024-02-01', 'end': '2024-02-28'})
        # Si openpyxl installé => 200, sinon redirection (302)
        self.assertIn(resp.status_code, (200, 302))
