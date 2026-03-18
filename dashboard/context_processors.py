from doors.models import Inquiry 


def dashboard_context(request):
    """Inject dashboard-global context (e.g. unread inquiry count)."""
    if not request.user.is_authenticated:
        return {}
    try:
        new_count = Inquiry.objects.filter(status='new').count()
    except Exception:
        new_count = 0
    return {
        'new_inquiry_count': new_count,
    }
