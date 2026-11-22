import os
import logging
import shutil

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from doors.models import Door, Inquiry
from .decorators import staff_required
from .forms import DoorProductForm
from .models import DashboardSession


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

def _safe_next_url(request):
    """Return ?next= only if it points back to THIS site; otherwise the dashboard home."""
    candidate = request.POST.get('next') or request.GET.get('next') or ''
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse('dashboard_home')

def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard_home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user and user.is_staff:
            login(request, user)

            # Log successful dashboard login
            try:
                DashboardSession.objects.create(
                    user=user,
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
            except Exception:
                logger.exception(
                    'Could not write dashboard login audit row'
                )
            messages.success(
                request,
                f'Welcome back, {user.first_name or user.username}!'
            )
            return redirect(_safe_next_url(request))

        else:
            messages.error(
                request,
                'Invalid credentials or insufficient permissions.'
            )

    return render(request, 'dashboard/login.html')

@require_POST
def dashboard_logout(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('dashboard_login')


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


# ─────────────────────────────────────────────
#  DASHBOARD HOME
# ─────────────────────────────────────────────

@staff_required
def dashboard_home(request):
    total_products = Door.objects.count()
    featured_count = Door.objects.filter(is_featured=True).count()
    new_inquiries = Inquiry.objects.filter(status='new').count()
    total_inquiries = Inquiry.objects.count()

    # Products by category
    category_stats = (
        Door.objects.values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Recent products
    recent_products = Door.objects.order_by('-created_at')[:5]

    # Recent inquiries
    recent_inquiries = (
        Inquiry.objects.select_related('door')
        .order_by('-created_at')[:5]
    )

    context = {
        'total_products': total_products,
        'featured_count': featured_count,
        'new_inquiries': new_inquiries,
        'total_inquiries': total_inquiries,
        'category_stats': category_stats,
        'recent_products': recent_products,
        'recent_inquiries': recent_inquiries,
        'page_title': 'Dashboard',
    }

    return render(request, 'dashboard/home.html', context)


# ─────────────────────────────────────────────
#  PRODUCT LIST
# ─────────────────────────────────────────────

@staff_required
def product_list(request):
    products = Door.objects.all()

    # Search
    search = request.GET.get('search', '').strip()

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # Category filter — icontains because category is comma-separated
    # e.g. "bedroom,main_entrance,office" — must match partial too
    category = request.GET.get('category', '')

    if category:
        products = products.filter(category__icontains=category)

    # Material filter
    material = request.GET.get('material', '')

    if material:
        products = products.filter(material=material)

    # Featured filter
    featured = request.GET.get('featured', '')

    if featured == '1':
        products = products.filter(is_featured=True)
    elif featured == '0':
        products = products.filter(is_featured=False)

    # Sort
    sort = request.GET.get('sort', '-created_at')

    valid_sorts = [
        'name',
        '-name',
        'price_min',
        '-price_min',
        'created_at',
        '-created_at',
    ]

    if sort in valid_sorts:
        products = products.order_by(sort)

    total = products.count()

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    context = {
        'products': products_page,
        'total': total,
        'search': search,
        'current_category': category,
        'current_material': material,
        'current_featured': featured,
        'current_sort': sort,
        'categories': Door.CATEGORY_CHOICES,
        'materials': Door.MATERIAL_CHOICES,
        'page_title': 'Products',
    }

    return render(request, 'dashboard/product_list.html', context)


# ─────────────────────────────────────────────
#  PRODUCT ADD
# ─────────────────────────────────────────────

@staff_required
def product_add(request):
    if request.method == 'POST':
        form = DoorProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=True)

            messages.success(
                request,
                f'✓ "{product.name}" has been added to your collection.'
            )

            return redirect('dashboard_products')

        else:
            messages.error(
                request,
                'Please fix the errors below before saving.'
            )

    else:
        form = DoorProductForm()

    context = {
        'form': form,
        'page_title': 'Add New Product',
        'action': 'add',
    }

    return render(request, 'dashboard/product_form.html', context)


# ─────────────────────────────────────────────
#  PRODUCT EDIT
# ─────────────────────────────────────────────

@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Door, pk=pk)

    if request.method == 'POST':
        form = DoorProductForm(
            request.POST,
            request.FILES,
            instance=product
        )

        if form.is_valid():
            product = form.save(commit=True)

            messages.success(
                request,
                f'✓ "{product.name}" has been updated.'
            )

            return redirect('dashboard_products')

        else:
            messages.error(
                request,
                'Please fix the errors below before saving.'
            )

    else:
        form = DoorProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'page_title': f'Edit — {product.name}',
        'action': 'edit',
        'existing_images': product.get_all_images(),
    }

    return render(request, 'dashboard/product_form.html', context)


# ─────────────────────────────────────────────
#  PRODUCT DELETE
# ─────────────────────────────────────────────

@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Door, pk=pk)
    name = product.name

    # Remove door's media folder
    door_dir = os.path.join(
        settings.MEDIA_ROOT,
        'doors',
        f'door_{pk}'
    )

    if os.path.exists(door_dir):
        shutil.rmtree(door_dir, ignore_errors=True)

    product.delete()

    messages.success(
        request,
        f'"{name}" has been removed from your collection.'
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'"{name}" deleted.'
        })

    return redirect('dashboard_products')


# ─────────────────────────────────────────────
#  IMAGE MANAGEMENT
# ─────────────────────────────────────────────

@staff_required
@require_POST
def remove_image(request, pk, slot):
    """Remove a specific image slot from a product."""

    product = get_object_or_404(Door, pk=pk)

    slot_map = {
        'main': 'image_main',
        '2': 'image_2',
        '3': 'image_3',
        '4': 'image_4',
    }

    field_name = slot_map.get(str(slot))

    if not field_name:
        return JsonResponse(
            {'success': False, 'error': 'Invalid slot'},
            status=400
        )

    field = getattr(product, field_name)

    if field:
        # Delete the actual file
        try:
            if os.path.exists(field.path):
                os.remove(field.path)
        except Exception:
            pass

        setattr(product, field_name, None)
        product.save(update_fields=[field_name])

    return JsonResponse({'success': True})


# ─────────────────────────────────────────────
#  INQUIRY MANAGEMENT
# ─────────────────────────────────────────────

@staff_required
def inquiry_list(request):
    inquiries = Inquiry.objects.select_related('door').all()

    status_filter = request.GET.get('status', '')

    if status_filter:
        inquiries = inquiries.filter(status=status_filter)

    search = request.GET.get('search', '').strip()

    if search:
        inquiries = inquiries.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(message__icontains=search)
        )

    paginator = Paginator(inquiries, 20)
    page = request.GET.get('page', 1)

    context = {
        'inquiries': paginator.get_page(page),
        'total': inquiries.count(),
        'new_count': Inquiry.objects.filter(status='new').count(),
        'status_choices': Inquiry.STATUS_CHOICES,
        'current_status': status_filter,
        'search': search,
        'page_title': 'Customer Inquiries',
    }

    return render(request, 'dashboard/inquiry_list.html', context)


@staff_required
@require_POST
def inquiry_update_status(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)

    new_status = request.POST.get('status')
    valid = [s[0] for s in Inquiry.STATUS_CHOICES]

    if new_status in valid:
        inquiry.status = new_status
        inquiry.save(update_fields=['status'])

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'status': new_status
            })

    return redirect('dashboard_inquiries')


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────