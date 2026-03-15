from django.db import models
from django.urls import reverse


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
        ('72',  '72"'),
        ('75',  '75"'),
        ('78',  '78"'),
        ('81',  '81"'),
        ('84',  '84"'),
        ('custom', 'Custom'),
    ]

    WIDTH_CHOICES = [
        ('26',  '26"'),
        ('28',  '28"'),
        ('30',  '30"'),
        ('32',  '32"'),
        ('34',  '34"'),
        ('36',  '36"'),
        ('custom', 'Custom'),
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

    image_main  = models.ImageField(upload_to='doors/')
    image_2     = models.ImageField(upload_to='doors/', blank=True, null=True)
    image_3     = models.ImageField(upload_to='doors/', blank=True, null=True)
    image_4     = models.ImageField(upload_to='doors/', blank=True, null=True)
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
        return ', '.join(labels) if labels else '\u2014'

    def get_category_display_list(self):
        cat_map = dict(self.CATEGORY_CHOICES)
        return [cat_map.get(c, c.title()) for c in self.get_category_list()]

    def get_height_list(self):
        return [h.strip() for h in self.height.split(',') if h.strip()]

    def get_height_display(self):
        h_map = dict(self.HEIGHT_CHOICES)
        labels = [h_map.get(h, h + '"') for h in self.get_height_list()]
        return ', '.join(labels) if labels else '\u2014'

    def get_height_display_list(self):
        # Returns list of (label, is_custom) tuples
        h_map = dict(self.HEIGHT_CHOICES)
        return [(h_map.get(h, h + '"'), h == 'custom') for h in self.get_height_list()]

    def get_width_list(self):
        return [w.strip() for w in self.width.split(',') if w.strip()]

    def get_width_display(self):
        w_map = dict(self.WIDTH_CHOICES)
        labels = [w_map.get(w, w + '"') for w in self.get_width_list()]
        return ', '.join(labels) if labels else '\u2014'

    def get_width_display_list(self):
        # Returns list of (label, is_custom) tuples
        w_map = dict(self.WIDTH_CHOICES)
        return [(w_map.get(w, w + '"'), w == 'custom') for w in self.get_width_list()]

    def get_thickness_list(self):
        return [t.strip() for t in self.thickness.split(',') if t.strip()]

    def get_thickness_display(self):
        t_map = dict(self.THICKNESS_CHOICES)
        labels = [t_map.get(t, t + ' mm') for t in self.get_thickness_list()]
        return ', '.join(labels) if labels else '\u2014'

    def get_thickness_display_list(self):
        t_map = dict(self.THICKNESS_CHOICES)
        return [t_map.get(t, t + ' mm') for t in self.get_thickness_list()]

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

    def get_finish_display_list(self):
        finish_map = dict(self.FINISH_CHOICES)
        return [finish_map.get(f, f.title()) for f in self.get_finish_list()]

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