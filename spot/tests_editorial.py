from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time
from .models import (
    Journalist,
    Driver,
    CoverageRequest,
    CoverageAssignment,
    AssignmentNotificationCampaign,
    AssignmentNotificationAttempt,
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
