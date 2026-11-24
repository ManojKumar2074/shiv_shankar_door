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
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
import os
import uuid
import logging

from .models import Door, Inquiry, DoorPreview
from .forms import InquiryForm, ContactForm, PreviewRequestForm

logger = logging.getLogger(__name__)

MAX_UPLOADED_HOUSE_IMAGE_BYTES = 10 * 1024 * 1024
MAX_EXISTING_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_INPUT_PIXELS = 40_000_000
MAX_IMAGE_PROCESSING_PIXELS = 8_000_000
MAX_IMAGE_DIMENSION = 10_000


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

    # Build a reusable querystring containing every active GET filter EXCEPT
    # 'page'. This is filter-agnostic by design — it doesn't hardcode
    # 'category', 'material', etc., so any filter present today (or added
    # later) is automatically preserved across pagination links.
    querydict = request.GET.copy()
    querydict.pop('page', None)
    querystring = querydict.urlencode()

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
        'querystring':      querystring,
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

    Validates all POST data before saving anything.
    Cleans up uploaded and generated files if processing fails.
    """
    doors = Door.objects.all()
    preview_result = None

    if request.method == 'POST':
        form = PreviewRequestForm(request.POST, request.FILES)

        if form.is_valid():
            door = form.cleaned_data['door_id']
            house_image = form.cleaned_data['house_image']

            rect = {
                'x': form.cleaned_data['rect_x'],
                'y': form.cleaned_data['rect_y'],
                'w': form.cleaned_data['rect_w'],
                'h': form.cleaned_data['rect_h'],
            }

            preview = DoorPreview(
                door=door,
                house_image=house_image,
            )
            preview.save()

            try:
                result_path = process_door_preview(preview, rect)

                if result_path:
                    preview.preview_image = result_path
                    preview.save()
                    preview_result = preview
                else:
                    logger.warning(
                        'AI preview returned no result for door pk=%s',
                        door.pk,
                    )
                    messages.error(
                        request,
                        'Preview generation failed. Please try again with a clearer photo.',
                    )

            except Exception:
                logger.exception(
                    'AI preview failed for door pk=%s',
                    door.pk,
                )
                messages.error(
                    request,
                    'Preview generation failed. Please try again with a clearer photo.',
                )

            if preview_result is None:
                if preview.preview_image:
                    preview.preview_image.delete(save=False)

                preview.house_image.delete(save=False)
                preview.delete()

        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    context = {
        'doors': doors,
        'preview_result': preview_result,
        'whatsapp_float_url': f"https://wa.me/{getattr(settings, 'WHATSAPP_NUMBER', '')}",
    }

    return render(request, 'doors/ai_preview.html', context)

def _read_image_from_storage(
    image_field,
    max_compressed_bytes=MAX_UPLOADED_HOUSE_IMAGE_BYTES,
    max_input_pixels=MAX_IMAGE_INPUT_PIXELS,
    max_processing_pixels=MAX_IMAGE_PROCESSING_PIXELS,
    max_dimension=MAX_IMAGE_DIMENSION,
):
    """
    Read an image through Django storage without requiring
    a local filesystem path.

    Metadata and compressed-size checks run before OpenCV decoding.
    Oversized decoded inputs are rejected; oversized processing inputs
    are downscaled to a bounded resolution.
    """
    import io
    import cv2
    import numpy as np
    from PIL import Image, UnidentifiedImageError

    if not image_field or not image_field.name:
        return None

    try:
        storage = image_field.storage
        image_name = image_field.name

        file_size = None
        if hasattr(image_field, 'size'):
            try:
                file_size = image_field.size
            except Exception:
                file_size = None
        if file_size is None and hasattr(storage, 'size'):
            try:
                file_size = storage.size(image_name)
            except Exception:
                file_size = None

        if (
            max_compressed_bytes is not None
            and file_size is not None
            and file_size > max_compressed_bytes
        ):
            return None

        with storage.open(image_name, 'rb') as image_file:
            chunks = []
            total_size = 0
            chunk_size = 64 * 1024

            while True:
                if max_compressed_bytes is not None:
                    remaining = (max_compressed_bytes + 1) - total_size
                    if remaining <= 0:
                        return None
                    to_read = min(chunk_size, remaining)
                else:
                    to_read = chunk_size

                chunk = image_file.read(to_read)
                if not chunk:
                    break

                chunks.append(chunk)
                total_size += len(chunk)

                if max_compressed_bytes is not None and total_size > max_compressed_bytes:
                    return None

        if total_size == 0:
            return None

        image_data = b''.join(chunks)

        try:
            with Image.open(io.BytesIO(image_data)) as pil_image:
                width, height = pil_image.size
        except (UnidentifiedImageError, OSError, ValueError):
            return None

        if width < 1 or height < 1:
            return None

        if max_dimension is not None and (width > max_dimension or height > max_dimension):
            return None

        if max_input_pixels is not None and width * height > max_input_pixels:
            return None

        image_array = np.frombuffer(image_data, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            return None

        height, width = image.shape[:2]
        if max_input_pixels is not None and height * width > max_input_pixels:
            return None

        if max_processing_pixels is not None and height * width > max_processing_pixels:
            scale = (max_processing_pixels / float(height * width)) ** 0.5
            target_width = max(1, int(width * scale))
            target_height = max(1, int(height * scale))

            while target_width * target_height > max_processing_pixels and (
                target_width > 1 or target_height > 1
            ):
                if target_width > 1:
                    target_width -= 1
                if target_height > 1 and target_width * target_height > max_processing_pixels:
                    target_height -= 1

            interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            image = cv2.resize(
                image,
                (target_width, target_height),
                interpolation=interpolation,
            )

            if image is None or image.size == 0:
                return None

        return image

    except Exception:
        logger.exception("Failed to read image from Django storage")
        return None


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
    flood_mask = cv2.inRange(door_img, (221, 221, 221), (255, 255, 255))

    # Step 2: Flood fill from image corners to find edge-connected background
    h, w = flood_mask.shape
    flood_fill_mask = np.zeros((h + 2, w + 2), np.uint8)

    for pt in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]:
        if flood_mask[pt[0], pt[1]] == 255:
            cv2.floodFill(flood_mask, flood_fill_mask, (pt[1], pt[0]), 128)

    # Pixels marked 128 are confirmed background (connected to image edges)
    bg_mask = np.empty_like(flood_mask)
    cv2.compare(flood_mask, 128, cv2.CMP_EQ, dst=bg_mask)

    # Step 3: Dilate mask to cover fringe/anti-aliased edge pixels
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cv2.dilate(bg_mask, kernel, dst=bg_mask, iterations=1)

    # Step 4: Blur mask edges for smooth transparency transition
    bg_soft = bg_mask.astype(np.float32)
    cv2.GaussianBlur(bg_soft, (5, 5), 0, dst=bg_soft)

    # Step 5: Apply alpha — invert so background=0, door=255
    np.subtract(255.0, bg_soft, out=bg_soft)
    np.clip(bg_soft, 0, 255, out=bg_soft)
    door_bgra[:, :, 3] = bg_soft.astype(np.uint8)

    return door_bgra


# ── CV Helper: Process Door Preview ──────────────────────────────────────────
def process_door_preview(preview, rect):
    """
    Composite a door image onto a house photo using OpenCV.

    Images are read and written through Django storage.
    No direct filesystem paths are required.

    Returns:
        str: Storage-relative filename.
        None: If processing fails.
    """

    import cv2
    import numpy as np
    import uuid

    saved_name = None
    candidate_name = None
    storage = preview.preview_image.storage

    try:
        # Step 1: Load images through Django storage.
        house_img = _read_image_from_storage(
            preview.house_image,
            max_compressed_bytes=MAX_UPLOADED_HOUSE_IMAGE_BYTES,
            max_input_pixels=MAX_IMAGE_INPUT_PIXELS,
            max_processing_pixels=MAX_IMAGE_PROCESSING_PIXELS,
            max_dimension=MAX_IMAGE_DIMENSION,
        )

        door_img = _read_image_from_storage(
            preview.door.image_main,
            max_compressed_bytes=MAX_EXISTING_PRODUCT_IMAGE_BYTES,
            max_input_pixels=MAX_IMAGE_INPUT_PIXELS,
            max_processing_pixels=MAX_IMAGE_PROCESSING_PIXELS,
            max_dimension=MAX_IMAGE_DIMENSION,
        )

        if house_img is None or door_img is None:
            return None

        h_height, h_width = house_img.shape[:2]

        # Step 2: Convert percentages into pixel coordinates.
        px = int((rect['x'] / 100.0) * h_width)
        py = int((rect['y'] / 100.0) * h_height)
        pw = int((rect['w'] / 100.0) * h_width)
        ph = int((rect['h'] / 100.0) * h_height)

        # Reject invalid rectangles instead of silently changing them.
        if (
            px < 0 or py < 0 or
            pw < 1 or ph < 1 or
            px + pw > h_width or
            py + ph > h_height
        ):
            return None

        # Step 3: Remove white background.
        door_bgra = remove_white_background(door_img)

        if door_bgra is None:
            return None

        # Step 4: Crop transparent padding.
        alpha_ch = door_bgra[:, :, 3]
        _, visible_mask = cv2.threshold(alpha_ch, 10, 255, cv2.THRESH_BINARY)
        x, y, w, h = cv2.boundingRect(visible_mask)

        if w == 0 or h == 0:
            return None

        y_min = max(0, y - 2)
        y_max = min(door_bgra.shape[0], y + h + 2)

        x_min = max(0, x - 2)
        x_max = min(door_bgra.shape[1], x + w + 2)

        door_bgra = door_bgra[y_min:y_max, x_min:x_max]

        # Step 5: Resize door.
        door_resized = cv2.resize(
            door_bgra,
            (pw, ph),
            interpolation=cv2.INTER_LANCZOS4
        )

        # Step 6: Brightness matching.
        roi = house_img[py:py + ph, px:px + pw]
        door_rgb = door_resized[:, :, :3]

        door_gray = cv2.cvtColor(door_rgb, cv2.COLOR_BGR2GRAY)
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        door_sum = 0.0
        roi_sum = 0.0
        visible_count = 0

        chunk_rows = 256
        for row_start in range(0, ph, chunk_rows):
            row_end = min(row_start + chunk_rows, ph)
            alpha_chunk = door_resized[row_start:row_end, :, 3] > 127
            if not np.any(alpha_chunk):
                continue

            door_chunk_gray = door_gray[row_start:row_end]
            roi_chunk_gray = roi_gray[row_start:row_end]

            visible_count += int(np.count_nonzero(alpha_chunk))
            door_sum += float(door_chunk_gray[alpha_chunk].sum(dtype=np.float64))
            roi_sum += float(roi_chunk_gray[alpha_chunk].sum(dtype=np.float64))

        brightness_ratio = 1.0
        if visible_count > 0:
            door_mean = (door_sum / visible_count) + 1e-6
            roi_mean = (roi_sum / visible_count) + 1e-6
            brightness_ratio = max(0.55, min(roi_mean / door_mean, 1.8))

        # Step 7: Alpha compositing (row chunks to limit peak memory).
        for row_start in range(0, ph, chunk_rows):
            row_end = min(row_start + chunk_rows, ph)

            door_rgb_chunk = door_resized[row_start:row_end, :, :3].astype(np.float32)
            alpha_chunk = (
                door_resized[row_start:row_end, :, 3:4].astype(np.float32) / 255.0
            )
            roi_chunk = roi[row_start:row_end].astype(np.float32)

            np.multiply(door_rgb_chunk, brightness_ratio, out=door_rgb_chunk)
            np.clip(door_rgb_chunk, 0, 255, out=door_rgb_chunk)

            blended = (
                door_rgb_chunk * alpha_chunk
                + roi_chunk * (1.0 - alpha_chunk)
            )

            roi[row_start:row_end] = blended.astype(np.uint8)

        # Step 8: Encode JPEG in memory.
        success, encoded_image = cv2.imencode(
            '.jpg',
            house_img,
            [cv2.IMWRITE_JPEG_QUALITY, 92]
        )

        if not success:
            raise RuntimeError("OpenCV JPEG encoding failed")

        # Step 9: Save through Django storage.
        filename = f"preview_{uuid.uuid4().hex}.jpg"
        candidate_name = f"previews/result/{filename}"

        saved_name = storage.save(
            candidate_name,
            ContentFile(encoded_image.tobytes())
        )

        if not saved_name:
            raise RuntimeError("Preview storage returned no filename")

        return saved_name

    except Exception:
        logger.exception(
            "Door preview processing failed for preview pk=%s",
            preview.pk
        )

        cleanup_names = []
        if candidate_name:
            cleanup_names.append(candidate_name)
        if saved_name and saved_name not in cleanup_names:
            cleanup_names.append(saved_name)

        for name in cleanup_names:
            try:
                if hasattr(storage, 'exists') and storage.exists(name):
                    storage.delete(name)
                elif not hasattr(storage, 'exists'):
                    storage.delete(name)
            except Exception:
                logger.exception(
                    "Failed to clean up generated preview file: %s",
                    name,
                )

        return None


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