from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from . import views


class SafeNextUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_external_next_url_falls_back_to_dashboard(self):
        request = self.factory.get(
            reverse('dashboard_login'),
            {'next': 'https://evil.example'},
            HTTP_HOST='localhost',
        )

        self.assertEqual(
            views._safe_next_url(request),
            reverse('dashboard_home'),
        )

    def test_internal_next_url_is_allowed(self):
        request = self.factory.get(
            reverse('dashboard_login'),
            {'next': '/dashboard/products/'},
            HTTP_HOST='localhost',
        )

        self.assertEqual(
            views._safe_next_url(request),
            '/dashboard/products/',
        )


class DashboardLogoutTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_request_is_rejected(self):
        request = self.factory.get(reverse('dashboard_logout'))
        response = views.dashboard_logout(request)

        self.assertEqual(response.status_code, 405)

    @patch('dashboard.views.logout')
    def test_post_request_logs_out_and_redirects(self, mock_logout):
        request = self.factory.post(reverse('dashboard_logout'))
        request.user = AnonymousUser()
        request.session = {}
        request._messages = SimpleNamespace(
            add=lambda *args, **kwargs: None
        )

        response = views.dashboard_logout(request)

        mock_logout.assert_called_once_with(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('dashboard_login'),
        )