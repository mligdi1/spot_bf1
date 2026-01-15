from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time
from django.urls import reverse
from unittest.mock import patch
from .models import (
    Journalist,
    Driver,
    CoverageRequest,
    CoverageAssignment,
    AssignmentNotificationCampaign,
    AssignmentNotificationAttempt,
    Notification,
)

User = get_user_model()

class EditorialPagesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='pass12345',
            role='editorial_manager'
        )
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin1@test.com',
            password='pass12345',
            role='admin'
        )
        self.client.login(username='manager', password='pass12345')
        self.journalist = Journalist.objects.create(
            name='John Doe', email='john@test.com', phone='+22670000000', status='available', specialties='politique,sport'
        )
        self.driver = Driver.objects.create(
            name='Driver One', phone='+22670000001', status='available'
        )
        self.coverage = CoverageRequest.objects.create(
            user=self.manager,
            event_title='Conférence de presse',
            event_type='press_conference',
            event_date=timezone.localdate(),
            start_time=time(10, 0),
            address='Ouagadougou',
            contact_name='Contact',
            contact_phone='+22670000002',
            coverage_type='video_report',
            status='review',
        )

    def test_editorial_support_chat_and_notification_on_message(self):
        resp = self.client.get(reverse('editorial_support_chat'), follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/editorial/chat/', resp['Location'])

        thread_id = resp['Location'].rstrip('/').split('/')[-1]
        thread_url = reverse('editorial_chat_thread', kwargs={'thread_id': thread_id})
        resp2 = self.client.get(thread_url)
        self.assertEqual(resp2.status_code, 200)

        resp3 = self.client.post(thread_url, {'content': 'Bonjour admin'}, follow=False)
        self.assertEqual(resp3.status_code, 302)
        from .models import Notification
        self.assertTrue(Notification.objects.filter(user=self.admin, related_thread__isnull=False).exists())

    def test_journalist_detail_json(self):
        url = reverse('editorial_api_journalist_detail', args=[self.journalist.id])
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data['item']['name'], 'John Doe')

    def test_driver_detail_json(self):
        url = reverse('editorial_api_driver_detail', args=[self.driver.id])
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data['item']['name'], 'Driver One')

    def test_journalist_delete(self):
        url = reverse('editorial_api_journalist_detail', args=[self.journalist.id])
        resp = self.client.delete(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('ok'))
        self.assertFalse(Journalist.objects.filter(id=self.journalist.id).exists())

    def test_driver_delete(self):
        url = reverse('editorial_api_driver_detail', args=[self.driver.id])
        resp = self.client.delete(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get('ok'))
        self.assertFalse(Driver.objects.filter(id=self.driver.id).exists())

    def test_journalist_update_inline(self):
        url = reverse('editorial_api_journalist_detail', args=[self.journalist.id])
        resp = self.client.post(
            url,
            data='{"phone":"+22671111111"}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        self.journalist.refresh_from_db()
        self.assertEqual(self.journalist.phone, '+22671111111')

    def test_driver_update_inline(self):
        url = reverse('editorial_api_driver_detail', args=[self.driver.id])
        resp = self.client.post(
            url,
            data='{"status":"offline"}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, 'offline')

    def test_assignment_creates_notification_campaigns(self):
        url = reverse('editorial_assign_coverage', args=[self.coverage.id])
        resp = self.client.post(url, data={'journalist_id': str(self.journalist.id), 'driver_id': str(self.driver.id)})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CoverageAssignment.objects.filter(coverage=self.coverage).exists())
        ass = CoverageAssignment.objects.filter(coverage=self.coverage).order_by('-assigned_at').first()
        camps = list(AssignmentNotificationCampaign.objects.filter(assignment=ass).order_by('created_at'))
        self.assertEqual(len(camps), 2)
        self.assertTrue(all(c.confirm_code for c in camps))
        self.assertTrue(AssignmentNotificationAttempt.objects.filter(campaign__in=camps, channel='email').exists())

    def test_web_confirmation_marks_campaign_confirmed(self):
        url = reverse('editorial_assign_coverage', args=[self.coverage.id])
        self.client.post(url, data={'journalist_id': str(self.journalist.id), 'driver_id': str(self.driver.id)})
        ass = CoverageAssignment.objects.filter(coverage=self.coverage).order_by('-assigned_at').first()
        camp = AssignmentNotificationCampaign.objects.filter(assignment=ass, recipient_kind='driver').first()
        confirm_url = reverse('assignment_confirm', args=[camp.id, camp.confirm_code])
        resp = self.client.get(confirm_url)
        self.assertEqual(resp.status_code, 200)
        camp.refresh_from_db()
        self.assertEqual(camp.status, 'confirmed')
        self.assertIsNotNone(camp.confirmed_at)
        self.assertTrue(AssignmentNotificationAttempt.objects.filter(campaign=camp, status='confirmed').exists())

    def test_sms_inbound_confirms_by_code(self):
        url = reverse('editorial_assign_coverage', args=[self.coverage.id])
        self.client.post(url, data={'journalist_id': str(self.journalist.id), 'driver_id': str(self.driver.id)})
        ass = CoverageAssignment.objects.filter(coverage=self.coverage).order_by('-assigned_at').first()
        camp = AssignmentNotificationCampaign.objects.filter(assignment=ass, recipient_kind='driver').first()
        inbound_url = reverse('sms_inbound')
        resp = self.client.post(inbound_url, data={'from': self.driver.phone, 'body': f'OK {camp.confirm_code}'})
        self.assertEqual(resp.status_code, 200)
        camp.refresh_from_db()
        self.assertEqual(camp.status, 'confirmed')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    OFFSITE_NOTIFICATIONS={
        'enabled': True,
        'dedupe_minutes': 60,
        'roles': {
            'client': {'email': True},
        },
    },
)
class OffsiteNotificationDeliveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='client1',
            email='client1@test.com',
            password='pass12345',
            role='client',
            phone='+22670000009',
        )

    def test_delivers_email_and_whatsapp_and_marks_status_fields(self):
        with patch('spot.signals.send_notification_email', return_value=True) as email_mock:
            with self.captureOnCommitCallbacks(execute=True):
                n = Notification.objects.create(user=self.user, title='Titre', message='Message', type='info')

        n.refresh_from_db()
        self.assertEqual(email_mock.call_count, 1)
        self.assertEqual(n.email_status, 'sent')
        self.assertIsNotNone(n.email_sent_at)
        self.assertEqual(n.email_error, '')

    def test_dedup_skips_second_notification(self):
        with patch('spot.signals.send_notification_email', return_value=True) as email_mock:
            with self.captureOnCommitCallbacks(execute=True):
                Notification.objects.create(user=self.user, title='Titre', message='Message', type='info')
            with self.captureOnCommitCallbacks(execute=True):
                n2 = Notification.objects.create(user=self.user, title='Titre', message='Message', type='info')

        n2.refresh_from_db()
        self.assertEqual(email_mock.call_count, 1)
        self.assertEqual((n2.email_status or '').strip(), '')
