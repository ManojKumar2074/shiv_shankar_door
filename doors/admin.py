from django.contrib import admin
from django.utils.html import format_html
from .models import Door, Inquiry, DoorPreview


class DoorAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'name', 'category', 'material', 'price_display', 'is_featured', 'created_at']
    list_display_links = ['thumbnail', 'name']
    list_filter = ['category', 'material', 'finish_type', 'is_featured']
    search_fields = ['name', 'description']
    list_editable = ['is_featured']
    readonly_fields = ['created_at', 'updated_at', 'preview_main_image']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'category', 'description', 'is_featured')
        }),
        ('Specifications', {
            'fields': ('material', 'finish_type', 'width', 'height', 'thickness')
        }),
        ('Pricing', {
            'fields': ('price_min', 'price_max')
        }),
        ('Images', {
            'fields': ('image_main', 'preview_main_image', 'image_2', 'image_3', 'image_4')
        }),
        ('Features', {
            'fields': ('features',),
            'description': 'Enter one feature per line'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def thumbnail(self, obj):
        if obj.image_main:
            return format_html('<img src="{}" width="60" height="70" style="object-fit:cover;border-radius:4px;" />', obj.image_main.url)
        return '—'
    thumbnail.short_description = ''

    def price_display(self, obj):
        return obj.get_price_display()
    price_display.short_description = 'Price Range'

    def preview_main_image(self, obj):
        if obj.image_main:
            return format_html('<img src="{}" width="200" style="border-radius:8px;" />', obj.image_main.url)
        return '—'
    preview_main_image.short_description = 'Main Image Preview'


class InquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'door', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'phone', 'email', 'message']
    list_editable = ['status']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Contact Info', {
            'fields': ('name', 'phone', 'email', 'location')
        }),
        ('Inquiry Details', {
            'fields': ('door', 'message', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('door')


class DoorPreviewAdmin(admin.ModelAdmin):
    list_display = ['door', 'preview_thumb', 'created_at']
    readonly_fields = ['created_at', 'preview_result']

    def preview_thumb(self, obj):
        if obj.preview_image:
            return format_html('<img src="{}" width="80" style="border-radius:4px;" />', obj.preview_image.url)
        return 'Processing...'
    preview_thumb.short_description = 'Preview'

    def preview_result(self, obj):
        if obj.preview_image:
            return format_html('<img src="{}" width="400" style="border-radius:8px;" />', obj.preview_image.url)
        return '—'
    preview_result.short_description = 'Generated Preview'


admin.site.register(Door, DoorAdmin)
admin.site.register(Inquiry, InquiryAdmin)
admin.site.register(DoorPreview, DoorPreviewAdmin)

admin.site.site_header = 'Shiv Shankar Door — Admin'
admin.site.site_title = 'SSD Admin'
admin.site.index_title = 'Door Portfolio Management'
