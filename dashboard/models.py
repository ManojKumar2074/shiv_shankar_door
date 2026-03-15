from django.db import models
from django.urls import reverse


def door_image_path(slot):
    """
    Returns a callable upload_to that saves images directly to
    media/doors/door_<pk>/<slot>.ext — no post-save moving needed.
    """
    import os as _os
    def _upload(instance, filename):
        ext = _os.path.splitext(filename)[1].lower() or '.jpg'
        return f'doors/door_{instance.pk}/{slot}{ext}'
    return _upload


class Door(models.Model):
    CATEGORY_CHOICES = [
        ('main_entrance', 'Main Entrance'),
        ('bedroom', 'Bedroom'),
        ('bathroom', 'Bathroom'),
        ('office', 'Office'),
        ('commercial', 'Commercial'),
        ('pooja', 'Pooja Room Door'),
    ]

    MATERIAL_CHOICES = [
        ('hard_wood', 'Hard Wood'),
        ('engineered_wood', 'Engineered Wood'),
        ('steel', 'Steel'),
        ('glass', 'Glass & Wood'),
        ('fiber', 'Fiber'),
        ('pvc', 'PVC'),
        ('aluminium', 'Aluminium'),
    ]

    HEIGHT_CHOICES = [
        ('1981', "1981 mm (6'6\")"),
        ('2032', "2032 mm (6'8\")"),
        ('2134', "2134 mm (7'0\")"),
        ('2286', "2286 mm (7'6\")"),
        ('2438', "2438 mm (8'0\")"),
        ('custom', 'Custom mm'),
    ]

    WIDTH_CHOICES = [
        ('610',  "610 mm (2'0\")"),
        ('686',  "686 mm (2'3\")"),
        ('762',  "762 mm (2'6\")"),
        ('813',  "813 mm (2'8\")"),
        ('838',  "838 mm (2'9\")"),
        ('864',  "864 mm (2'10\")"),
        ('914',  "914 mm (3'0\")"),
        ('1016', "1016 mm (3'4\")"),
        ('1067', "1067 mm (3'6\")"),
        ('1200', "1200 mm (3'11\")"),
        ('custom', 'Custom mm'),
    ]

    THICKNESS_CHOICES = [
        ('30', '30 mm'),
        ('32', '32 mm'),
        ('33', '33 mm'),
        ('35', '35 mm'),
        ('38', '38 mm'),
        ('40', '40 mm'),
        ('45', '45 mm'),
    ]

    SFT_RATE_CHOICES = [
        ('270', '₹270 per sq.ft'),
        ('300', '₹300 per sq.ft'),
        ('325', '₹325 per sq.ft'),
        ('custom', 'Custom / On Request'),
    ]

    FINISH_CHOICES = [
        ('matte', 'Matte'),
        ('gloss', 'Gloss'),
        ('satin', 'Satin'),
        ('textured', 'Textured'),
        ('natural', 'Natural Wood'),
        ('lacquered', 'Lacquered'),
    ]

    name        = models.CharField(max_length=200)
    category    = models.CharField(max_length=200, help_text='One or more categories, comma-separated')
    material    = models.CharField(max_length=50, choices=MATERIAL_CHOICES)
    description = models.TextField()

    height    = models.CharField(max_length=200, help_text='One or more heights, comma-separated')
    width     = models.CharField(max_length=200, help_text='One or more widths, comma-separated')
    thickness = models.CharField(max_length=200, help_text='One or more thicknesses, comma-separated')

    finish_type = models.CharField(
        max_length=200,
        help_text="One or more finishes, comma-separated (e.g. matte,gloss)"
    )

    # FIX: Single price field for Pooja Room doors (no min/max range)
    price_min = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Pooja Room doors only — price in ₹"
    )
    price_max = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Deprecated — no longer used. Kept for data migration only."
    )

    # Sq.ft rate — all non-Pooja doors (optional, not required)
    sft_rate = models.CharField(
        max_length=20, choices=SFT_RATE_CHOICES, blank=True, null=True,
        help_text="Rate per sq.ft — for all doors except Pooja Room"
    )

    image_main  = models.ImageField(upload_to=door_image_path('main'))
    image_2     = models.ImageField(upload_to=door_image_path('photo2'), blank=True, null=True)
    image_3     = models.ImageField(upload_to=door_image_path('photo3'), blank=True, null=True)
    image_4     = models.ImageField(upload_to=door_image_path('photo4'), blank=True, null=True)
    features    = models.TextField(help_text="One feature per line", blank=True)
    is_featured = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('door_detail', args=[self.pk])

    def get_features_list(self):
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def is_pooja(self):
        # Support both single 'pooja' and comma-separated containing 'pooja'
        return 'pooja' in [c.strip() for c in self.category.split(',')]

    def get_category_list(self):
        return [c.strip() for c in self.category.split(',') if c.strip()]

    def get_category_display(self):
        cat_map = dict(self.CATEGORY_CHOICES)
        labels = [cat_map.get(c, c.title()) for c in self.get_category_list()]
        return ', '.join(labels) if labels else '—'

    def get_height_list(self):
        return [h.strip() for h in self.height.split(',') if h.strip()]

    def get_height_display(self):
        h_map = dict(self.HEIGHT_CHOICES)
        labels = [h_map.get(h, h + ' mm') for h in self.get_height_list()]
        return ', '.join(labels) if labels else '—'

    def get_width_list(self):
        return [w.strip() for w in self.width.split(',') if w.strip()]

    def get_width_display(self):
        w_map = dict(self.WIDTH_CHOICES)
        labels = [w_map.get(w, w + ' mm') for w in self.get_width_list()]
        return ', '.join(labels) if labels else '—'

    def get_thickness_list(self):
        return [t.strip() for t in self.thickness.split(',') if t.strip()]

    def get_thickness_display(self):
        t_map = dict(self.THICKNESS_CHOICES)
        labels = [t_map.get(t, t + ' mm') for t in self.get_thickness_list()]
        return ', '.join(labels) if labels else '—'

    def get_price_display(self):
        """
        Pooja doors  → single fixed ₹ price
        Other doors  → rate per sq.ft (optional)
        """
        if self.is_pooja():
            if self.price_min:
                return f"₹{self.price_min:,}"
            return "Price on request"
        # Non-pooja
        if self.sft_rate and self.sft_rate != 'custom':
            return f"₹{self.sft_rate} / sq.ft"
        return "Price on request"

    def get_finish_list(self):
        return [f.strip() for f in self.finish_type.split(',') if f.strip()]

    def get_finish_display(self):
        finish_map = dict(self.FINISH_CHOICES)
        labels = [finish_map.get(f, f.title()) for f in self.get_finish_list()]
        return ' & '.join(labels) if labels else '—'

    # Alias used in door_detail.html specs table
    def get_finish_type_display(self):
        return self.get_finish_display()

    def get_all_images(self):
        images = [self.image_main]
        for img in [self.image_2, self.image_3, self.image_4]:
            if img:
                images.append(img)
        return images


class Inquiry(models.Model):
    STATUS_CHOICES = [
        ('new',       'New'),
        ('contacted', 'Contacted'),
        ('quoted',    'Quoted'),
        ('closed',    'Closed'),
    ]
    door     = models.ForeignKey(Door, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiries')
    name     = models.CharField(max_length=100)
    phone    = models.CharField(max_length=15)
    email    = models.EmailField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    message  = models.TextField()
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Inquiries'

    def __str__(self):
        door_name = self.door.name if self.door else "General"
        return f"{self.name} — {door_name} ({self.created_at.strftime('%d %b %Y')})"


class DoorPreview(models.Model):
    door          = models.ForeignKey(Door, on_delete=models.CASCADE, related_name='previews')
    house_image   = models.ImageField(upload_to='previews/house/')
    preview_image = models.ImageField(upload_to='previews/result/', blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Preview: {self.door.name} — {self.created_at.strftime('%d %b %Y')}"