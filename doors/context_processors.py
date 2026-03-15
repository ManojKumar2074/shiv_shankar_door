from django.conf import settings


def site_context(request):
    return {
        'site_name': 'Shiv Shankar Door',
        'whatsapp_number': settings.WHATSAPP_NUMBER,
        'business_phone_1': settings.BUSINESS_PHONE_1,
        'business_phone_2': settings.BUSINESS_PHONE_2,
        'business_email': settings.BUSINESS_EMAIL,
        'maps_url': settings.MAPS_URL,
        'whatsapp_float_url': f"https://wa.me/{settings.WHATSAPP_NUMBER}?text=Hello, I'm interested in your door designs.",
    }
