from django.contrib import admin

from .models import ImageAsset, SiteChrome


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'alt', 'slot', 'sort_order', 'site', 'content_type', 'size', 'created_at')
    list_filter = ('site', 'slot', 'content_type')
    search_fields = ('title', 'alt', 'storage_key', 'slot')
    readonly_fields = (
        'id', 'content_type', 'size', 'width', 'height',
        'storage_key', 'url', 'created_at', 'updated_at',
    )
    ordering = ('sort_order', 'created_at')


@admin.register(SiteChrome)
class SiteChromeAdmin(admin.ModelAdmin):
    list_display = ('site', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
