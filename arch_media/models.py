import uuid
from pathlib import Path

from django.db import models


def arch_upload_to(instance, filename):
    """Store bytes on the default storage backend, never in Postgres."""
    ext = Path(filename).suffix.lower()[:12] or '.bin'
    site = instance.site or 'arch'
    return f'arch/{site}/{instance.id}{ext}'


class ImageAsset(models.Model):
    """Arch image library metadata. File bytes live on MEDIA_ROOT or S3/R2."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    alt = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(upload_to=arch_upload_to, max_length=500)
    storage_key = models.CharField(max_length=500, blank=True)
    url = models.CharField(max_length=1000, blank=True)
    sort_order = models.IntegerField(default=0)
    slot = models.CharField(max_length=100, blank=True)
    site = models.CharField(max_length=50, default='arch')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['site', 'sort_order']),
            models.Index(fields=['site', 'slot']),
        ]

    def __str__(self):
        return self.title or self.alt or str(self.id)

    def refresh_storage_fields(self):
        if self.file:
            self.storage_key = self.file.name
            try:
                self.url = self.file.url
            except ValueError:
                self.url = ''

    def save(self, *args, **kwargs):
        # Persist the file first so storage_key/url match the stored object.
        super().save(*args, **kwargs)
        if kwargs.get('update_fields') is not None:
            return
        if self.file and (self.storage_key != self.file.name or not self.url):
            self.refresh_storage_fields()
            super().save(update_fields=['storage_key', 'url', 'updated_at'])

    def delete(self, *args, **kwargs):
        storage, name = (self.file.storage, self.file.name) if self.file else (None, None)
        super().delete(*args, **kwargs)
        if storage and name:
            storage.delete(name)


class SiteChrome(models.Model):
    """Singleton-per-site JSON document for Arch chrome (nav, theme, copy)."""

    site = models.CharField(max_length=50, unique=True, default='arch')
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site chrome'
        verbose_name_plural = 'Site chrome'

    def __str__(self):
        return f'chrome:{self.site}'
