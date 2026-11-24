from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
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


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.render_patcher = patch(
            'dashboard.views.render',
            side_effect=lambda request, template, context=None, status=None:
                HttpResponse(status=status or 200),
        )
        self.render_patcher.start()

        User.objects.create_user(
            username='owner',
            password='right-pass-123',
            is_staff=True,
        )

    def tearDown(self):
        self.render_patcher.stop()
        cache.clear()

    def _post(self, password):
        return self.client.post(
            reverse('dashboard_login'),
            {
                'username': 'owner',
                'password': password,
            },
            HTTP_HOST='localhost',
        )

    def test_locks_after_five_failures(self):
        codes = [
            self._post('wrong').status_code
            for _ in range(7)
        ]

        self.assertEqual(
            codes,
            [200, 200, 200, 200, 200, 429, 429],
        )

    def test_correct_password_blocked_while_locked(self):
        for _ in range(5):
            self._post('wrong')

        response = self._post('right-pass-123')

        self.assertEqual(response.status_code, 429)

    def test_success_clears_counter(self):
        for _ in range(3):
            self._post('wrong')

        response = self._post('right-pass-123')

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            cache.get('dash-login:owner', 0),
            0,
        )

    def test_changing_forwarded_ip_does_not_bypass_lock(self):
        for i in range(5):
            self.client.post(
                reverse('dashboard_login'),
                {
                    'username': 'owner',
                    'password': 'wrong',
                },
                HTTP_HOST='localhost',
                HTTP_X_FORWARDED_FOR=f'10.0.0.{i}',
            )

        response = self.client.post(
            reverse('dashboard_login'),
            {
                'username': 'owner',
                'password': 'wrong',
            },
            HTTP_HOST='localhost',
            HTTP_X_FORWARDED_FOR='10.9.9.9',
        )

        self.assertEqual(response.status_code, 429)
