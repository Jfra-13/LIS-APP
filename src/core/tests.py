import uuid

from django.test import TestCase
from django.urls import reverse

from core.models import User


class CoreMvp0Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='demo', password='demo-pass-123')

    def test_user_uses_uuid_primary_key(self):
        self.assertIsInstance(self.user.id, uuid.UUID)

    def test_landing_redirects_authenticated_users(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('landing'))
        self.assertRedirects(response, reverse('home'))

    def test_home_requires_authentication(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_login_flow_works(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'demo', 'password': 'demo-pass-123'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MVP0 base')
        self.assertTrue(response.context['user'].is_authenticated)

