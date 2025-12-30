from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class EditorialAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='editor', password='pass1234', role='editorial_manager')

    def test_redirect_on_standard_endpoints(self):
        self.client.login(username='editor', password='pass1234')
        blocked = [
            'campaign_list',
            'campaign_create',
            'spot_list',
            'broadcast_grid',
            'correspondence_list',
            'advisory_wizard',
            'guides_list',
            'inspiration',
            'pricing_overview',
            'report_overview',
            'dashboard',
        ]
        for name in blocked:
            url = reverse(name)
            resp = self.client.get(url, follow=False)
            self.assertEqual(resp.status_code, 302)

    def test_editorial_dashboard_access(self):
        self.client.login(username='editor', password='pass1234')
        url = reverse('editorial_dashboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)