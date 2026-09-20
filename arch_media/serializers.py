from rest_framework import serializers

from .models import ImageAsset, SiteChrome


class ImageAssetSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ImageAsset
        fields = [
            'id',
            'title',
            'alt',
            'content_type',
            'size',
            'width',
            'height',
            'storage_key',
            'url',
            'sort_order',
            'slot',
            'site',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_url(self, obj):
        url = obj.url or ''
        if obj.file:
            try:
                url = obj.file.url or url
            except ValueError:
                pass
        request = self.context.get('request')
        if request and url and not url.startswith(('http://', 'https://')):
            return request.build_absolute_uri(url)
        return url


class ImageAssetPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageAsset
        fields = ['title', 'alt', 'sort_order', 'slot']


class ReorderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sort_order = serializers.IntegerField()
    slot = serializers.CharField(required=False, allow_blank=True, max_length=100)


class SiteChromeSerializer(serializers.ModelSerializer):
    chrome = serializers.JSONField(source='data')

    class Meta:
        model = SiteChrome
        fields = ['site', 'chrome', 'updated_at']
        read_only_fields = ['site', 'updated_at']
