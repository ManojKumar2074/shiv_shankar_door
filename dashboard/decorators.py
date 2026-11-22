from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse


def staff_required(view_func):
    """
    Anonymous users are redirected to dashboard login.
    Authenticated non-staff users receive HTTP 403.
    Active staff users can access the view.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                reverse('dashboard_login')
            )

        if not (user.is_active and user.is_staff):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper
