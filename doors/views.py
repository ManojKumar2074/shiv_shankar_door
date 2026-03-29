# ============================================================
# SHIV SHANKAR DOOR — doors/views.py
# Public-facing views: home, gallery, door detail, AI preview,
# about, and contact pages.
# ============================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Min, Max
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.core.paginator import Paginator
import os
import uuid

from .models import Door, Inquiry, DoorPreview
from .forms import InquiryForm, ContactForm


# ── Home Page ─────────────────────────────────────────────────────────────────
def home(request):
    """
    Renders the homepage with:
    - Featured doors (marked is_featured=True, max 6)
    - Latest doors (most recently added, max 8)
    - Category grid with door count and thumbnail per category
    - Total door count for the hero stats section
    """
    featured_doors = Door.objects.filter(is_featured=True)[:6]
    latest_doors   = Door.objects.all()[:8]

    # Build category data — use icontains since category is comma-separated
    # e.g. a door can belong to "main_entrance,bedroom"
    category_data = []
    for cat_key, cat_label in Door.CATEGORY_CHOICES:
        doors_in_cat = Door.objects.filter(category__icontains=cat_key)
        count = doors_in_cat.count()
        if count > 0:
            # Use the first door's image as the category thumbnail
            door = doors_in_cat.first()
            category_data.append({
                'key':   cat_key,
                'label': cat_label,
                'count': count,
                'image': door.image_main if door else None,
            })

    context = {
        'featured_doors':    featured_doors,
        'latest_doors':      latest_doors,
        'category_data':     category_data,
        'total_doors':       Door.objects.count(),
        'whatsapp_float_url': f"https://wa.me/{getattr(settings, 'WHATSAPP_NUMBER', '')}",
        'business_phone_1':  getattr(settings, 'BUSINESS_PHONE_1', ''),
    }
    return render(request, 'doors/home.html', context)


# ── Gallery Page ──────────────────────────────────────────────────────────────
def gallery(request):
    """
    Renders the door collection gallery with filtering and pagination.

    Filters supported (via GET params):
    - category : matches comma-separated category field using icontains
    - material : exact match on material field
    - finish   : matches comma-separated finish_type field using icontains
    - search   : searches door name and description
    - price_max: filters pooja doors by max fixed price

    Results are paginated — 12 doors per page.
    """
    doors = Door.objects.all()

    # Read filter values from GET parameters
    category  = request.GET.get('category', '')
    material  = request.GET.get('material', '')
    finish    = request.GET.get('finish', '')
    search    = request.GET.get('search', '')
    price_max = request.GET.get('price_max', '')

    # Apply filters — icontains used for comma-separated fields
    if category:
        doors = doors.filter(category__icontains=category)
    if material:
        doors = doors.filter(material=material)
    if finish:
        doors = doors.filter(finish_type__icontains=finish)
    if search:
        doors = doors.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    if price_max:
        try:
            doors = doors.filter(price_min__lte=int(price_max))
        except ValueError:
            pass  # Ignore invalid price_max values

    # Get price range for filter UI (used by price slider if enabled)
    price_range = Door.objects.aggregate(
        min_price=Min('price_min'),
        max_price=Max('price_max')
    )

    # Paginate results — 12 per page
    paginator  = Paginator(doors, 12)
    page       = request.GET.get('page', 1)
    doors_page = paginator.get_page(page)

    context = {
        'doors':            doors_page,
        'total_results':    doors.count(),
        'categories':       Door.CATEGORY_CHOICES,
        'materials':        Door.MATERIAL_CHOICES,
        'finishes':         Door.FINISH_CHOICES,
        'current_category': category,
        'current_material': material,
        'current_finish':   finish,
        'current_search':   search,
        'current_price_max': price_max,
        'price_range':      price_range,
    }
    return render(request, 'doors/gallery.html', context)


# ── Door Detail Page ──────────────────────────────────────────────────────────
def door_detail(request, pk):
    """
    Renders the detail page for a single door.

    - Shows all door specs, images, price calculator
    - Handles inquiry form submission (POST)
    - Shows related doors from the same category (max 4)
    - Generates a pre-filled WhatsApp message URL
    """
    door = get_object_or_404(Door, pk=pk)

    # Find related doors by matching the first category of this door
    first_cat = door.get_category_list()[0] if door.get_category_list() else ''
    related_doors = (
        Door.objects.filter(category__icontains=first_cat).exclude(pk=pk)[:4]
        if first_cat
        else Door.objects.exclude(pk=pk)[:4]
    )

    # Handle inquiry form submission
    if request.method == 'POST':
        form = InquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.door = door  # Link inquiry to this door
            inquiry.save()
            messages.success(
                request,
                'Your inquiry has been received. We will contact you within 24 hours.'
            )
            return redirect('door_detail', pk=pk)
    else:
        form = InquiryForm()

    # Build pre-filled WhatsApp message URL for the enquire button
    whatsapp_msg = f"Hello, I'm interested in {door.name}. Please provide more details."
    whatsapp_url = f"https://wa.me/{getattr(settings, 'WHATSAPP_NUMBER', '')}?text={whatsapp_msg}"

    context = {
        'door':          door,
        'related_doors': related_doors,
        'form':          form,
        'whatsapp_url':  whatsapp_url,
        'images':        door.get_all_images(),  # Main + up to 3 extra images
    }
    return render(request, 'doors/door_detail.html', context)


# ── AI Door Preview Page ──────────────────────────────────────────────────────
def ai_preview(request):
    """
    Renders the AI preview tool page.

    On GET  : Shows the tool with door selector and upload area.
    On POST : Processes the uploaded house photo + drawn rectangle,
              overlays the selected door onto the house image using
              OpenCV, and returns the before/after result.

    Rectangle coordinates are sent as percentages (0–100) of the
    displayed image size, then converted to actual pixels server-side.
    """
    doors         = Door.objects.all()
    preview_result = None
    error_msg      = None

    if request.method == 'POST':
        door_id     = request.POST.get('door_id')
        house_image = request.FILES.get('house_image')

        # Rectangle coordinates from canvas drawing (as % of image size)
        rect_x = request.POST.get('rect_x')
        rect_y = request.POST.get('rect_y')
        rect_w = request.POST.get('rect_w')
        rect_h = request.POST.get('rect_h')

        # Validate required inputs
        if not door_id or not house_image:
            error_msg = 'Please upload a photo and select a door.'
        elif not all([rect_x, rect_y, rect_w, rect_h]):
            error_msg = 'Please draw a rectangle on your photo to mark where the door is.'
        else:
            door    = get_object_or_404(Door, pk=door_id)
            preview = DoorPreview(door=door, house_image=house_image)
            preview.save()

            try:
                # Convert string percentages to float dict
                rect = {
                    'x': float(rect_x),
                    'y': float(rect_y),
                    'w': float(rect_w),
                    'h': float(rect_h),
                }
                result_path = process_door_preview(preview, rect)
                if result_path:
                    preview.preview_image = result_path
                    preview.save()
                    preview_result = preview
                else:
                    error_msg = 'Preview generation failed. Please try again with a clearer photo.'
            except Exception as e:
                error_msg = f'Preview generation failed: {str(e)}'

        if error_msg:
            messages.error(request, error_msg)

    context = {
        'doors':             doors,
        'preview_result':    preview_result,
        'whatsapp_float_url': f"https://wa.me/{getattr(settings, 'WHATSAPP_NUMBER', '')}",
    }
    return render(request, 'doors/ai_preview.html', context)


# ── CV Helper: Remove White Background ───────────────────────────────────────
def remove_white_background(door_img):
    """
    Remove white/near-white background from a door product image.

    Strategy:
    1. Threshold pixels where R, G, B all > 220 as potential background
    2. Flood fill from all 4 corners to isolate edge-connected white areas
       (this avoids removing white parts of the door itself)
    3. Dilate the background mask slightly to clean fringe pixels
    4. Gaussian blur the mask edge for soft anti-aliased transparency
    5. Set the alpha channel: 0 = background, 255 = door

    Returns the door image as BGRA (4-channel) with transparent background.
    Works best with product photos on plain white/light studio backgrounds.
    """
    import cv2
    import numpy as np

    # Add alpha channel to image (BGR → BGRA)
    door_bgra = cv2.cvtColor(door_img, cv2.COLOR_BGR2BGRA)

    # Step 1: Create white pixel mask (all channels > 220)
    b, g, r   = door_img[:, :, 0], door_img[:, :, 1], door_img[:, :, 2]
    white_mask = ((b > 220) & (g > 220) & (r > 220)).astype(np.uint8) * 255

    # Step 2: Flood fill from image corners to find edge-connected background
    h, w            = white_mask.shape
    flood_mask      = white_mask.copy()
    flood_fill_mask = np.zeros((h + 2, w + 2), np.uint8)

    for pt in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]:
        if white_mask[pt[0], pt[1]] == 255:
            cv2.floodFill(flood_mask, flood_fill_mask, (pt[1], pt[0]), 128)

    # Pixels marked 128 are confirmed background (connected to image edges)
    bg_mask = (flood_mask == 128).astype(np.uint8) * 255

    # Step 3: Dilate mask to cover fringe/anti-aliased edge pixels
    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    bg_mask = cv2.dilate(bg_mask, kernel, iterations=1)

    # Step 4: Blur mask edges for smooth transparency transition
    bg_soft = cv2.GaussianBlur(bg_mask.astype(np.float32), (5, 5), 0)

    # Step 5: Apply alpha — invert so background=0, door=255
    alpha              = np.clip(255 - bg_soft, 0, 255).astype(np.uint8)
    door_bgra[:, :, 3] = alpha

    return door_bgra


# ── CV Helper: Process Door Preview ──────────────────────────────────────────
def process_door_preview(preview, rect):
    """
    Composite a door image onto a house photo using OpenCV.

    Steps:
    1. Load house and door images from disk
    2. Convert rect percentages → actual pixel coordinates
    3. Remove white background from door image (get BGRA)
    4. Tight-crop door to remove transparent padding
    5. Resize door to fill the drawn rectangle
    6. Match door brightness to the house ROI for realism
    7. Alpha composite: blend door over house using door's alpha channel
    8. Save result as JPEG and return relative path

    Args:
        preview : DoorPreview model instance (has house_image and door FK)
        rect    : dict with x, y, w, h as floats (0.0–100.0 = % of image)

    Returns:
        str  : relative path to saved result image (e.g. 'previews/result/xxx.jpg')
        None : if processing fails for any reason
    """
    try:
        import cv2
        import numpy as np

        # Load images from disk
        house_path = preview.house_image.path
        door_path  = preview.door.image_main.path
        house_img  = cv2.imread(house_path)
        door_img   = cv2.imread(door_path)

        if house_img is None or door_img is None:
            return None  # Could not read one of the images

        h_height, h_width = house_img.shape[:2]

        # Convert percentage rect → pixel coordinates
        px = int((rect['x'] / 100.0) * h_width)
        py = int((rect['y'] / 100.0) * h_height)
        pw = int((rect['w'] / 100.0) * h_width)
        ph = int((rect['h'] / 100.0) * h_height)

        # Clamp coordinates to stay within image bounds
        px = max(0, min(px, h_width - 1))
        py = max(0, min(py, h_height - 1))
        pw = max(10, min(pw, h_width - px))
        ph = max(10, min(ph, h_height - py))

        # Step 1: Remove white background → BGRA door image
        door_bgra = remove_white_background(door_img)

        # Step 2: Tight crop — remove transparent padding around door
        # This prevents the door from appearing small inside a padded box
        alpha_ch        = door_bgra[:, :, 3]
        non_transparent = np.where(alpha_ch > 10)
        if len(non_transparent[0]) > 0 and len(non_transparent[1]) > 0:
            y_min = int(non_transparent[0].min())
            y_max = int(non_transparent[0].max())
            x_min = int(non_transparent[1].min())
            x_max = int(non_transparent[1].max())
            pad   = 2  # Small padding so edges aren't clipped
            y_min = max(0, y_min - pad)
            y_max = min(door_bgra.shape[0] - 1, y_max + pad)
            x_min = max(0, x_min - pad)
            x_max = min(door_bgra.shape[1] - 1, x_max + pad)
            door_bgra = door_bgra[y_min:y_max + 1, x_min:x_max + 1]

        # Step 3: Resize door to fill the user-drawn rectangle
        door_resized = cv2.resize(door_bgra, (pw, ph), interpolation=cv2.INTER_LANCZOS4)

        # Step 4: Brightness matching — make door fit the lighting of the scene
        result     = house_img.copy()
        roi        = result[py:py + ph, px:px + pw]
        door_rgb   = door_resized[:, :, :3]
        door_alpha = door_resized[:, :, 3].astype(np.float32) / 255.0

        # Sample only non-transparent pixels for accurate brightness comparison
        door_gray  = cv2.cvtColor(door_rgb, cv2.COLOR_BGR2GRAY).astype(np.float32)
        roi_gray   = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).astype(np.float32)
        door_pixels = door_gray[door_alpha > 0.5]
        roi_pixels  = roi_gray[door_alpha > 0.5]

        if len(door_pixels) > 0 and len(roi_pixels) > 0:
            door_mean        = np.mean(door_pixels) + 1e-6
            roi_mean         = np.mean(roi_pixels) + 1e-6
            brightness_ratio = float(roi_mean / door_mean)
            # Clamp ratio to avoid extreme over/under exposure
            brightness_ratio = max(0.55, min(brightness_ratio, 1.8))
        else:
            brightness_ratio = 1.0  # No adjustment if sampling failed

        door_adjusted = np.clip(
            door_rgb.astype(np.float32) * brightness_ratio, 0, 255
        ).astype(np.uint8)

        # Step 5: Alpha composite — blend door over house pixel by pixel
        # Formula: output = door * alpha + house * (1 - alpha)
        alpha_3ch  = np.stack([door_alpha, door_alpha, door_alpha], axis=2)
        roi_f      = roi.astype(np.float32)
        door_f     = door_adjusted.astype(np.float32)
        composited = door_f * alpha_3ch + roi_f * (1.0 - alpha_3ch)
        result[py:py + ph, px:px + pw] = composited.astype(np.uint8)

        # Step 6: Save result image to disk
        result_dir      = os.path.join(settings.MEDIA_ROOT, 'previews', 'result')
        os.makedirs(result_dir, exist_ok=True)
        result_filename  = f"preview_{uuid.uuid4().hex[:8]}.jpg"
        result_full_path = os.path.join(result_dir, result_filename)
        cv2.imwrite(result_full_path, result, [cv2.IMWRITE_JPEG_QUALITY, 92])

        return f"previews/result/{result_filename}"

    except Exception:
        return None  # Silently fail — caller shows user-friendly error


# ── About Page ────────────────────────────────────────────────────────────────
def about(request):
    """Renders the static About / Our Story page."""
    return render(request, 'doors/about.html')


# ── Contact Page ──────────────────────────────────────────────────────────────
def contact(request):
    """
    Renders the contact page with a general inquiry form.

    On POST: Saves a general Inquiry (no door linked) and redirects
             back to contact page with a success message.
    On GET : Shows the empty contact form.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save general inquiry — not linked to any specific door
            inquiry = Inquiry(
                name    = form.cleaned_data['name'],
                phone   = form.cleaned_data['phone'],
                email   = form.cleaned_data.get('email', ''),
                message = form.cleaned_data['message'],
            )
            inquiry.save()
            messages.success(
                request,
                'Thank you for reaching out. We will get back to you shortly.'
            )
            return redirect('contact')
    else:
        form = ContactForm()

    context = {
        'form':              form,
        'business_phone_1':  getattr(settings, 'BUSINESS_PHONE_1', ''),
        'business_phone_2':  getattr(settings, 'BUSINESS_PHONE_2', ''),
        'business_email':    getattr(settings, 'BUSINESS_EMAIL', ''),
        'maps_url':          getattr(settings, 'MAPS_URL', '#'),
        'whatsapp_float_url': f"https://wa.me/{getattr(settings, 'WHATSAPP_NUMBER', '')}",
    }
    return render(request, 'doors/contact.html', context)