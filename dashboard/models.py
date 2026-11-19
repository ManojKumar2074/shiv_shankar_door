from django.conf import settings
from django.db import models


class DashboardSession(models.Model):
    """Audit log: one row per successful dashboard login."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-login_time']

    def __str__(self):
        return f'{self.user} @ {self.login_time:%Y-%m-%d %H:%M}'