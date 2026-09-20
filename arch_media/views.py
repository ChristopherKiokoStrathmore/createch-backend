import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from PIL import Image, UnidentifiedImageError
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ImageAsset, SiteChrome
from .permissions import is_arch_admin
from .serializers import (
    ImageAssetPatchSerializer,
    ImageAssetSerializer,
    ReorderItemSerializer,
    SiteChromeSerializer,
)

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = frozenset(getattr(settings, 'ARCH_ALLOWED_CONTENT_TYPES', [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
]))
MAX_UPLOAD_BYTES = int(getattr(settings, 'ARCH_MAX_UPLOAD_BYTES', 12 * 1024 * 1024))
DEFAULT_SITE = 'arch'


def _admin_gate(request):
    if is_arch_admin(request):
        return None
    return Response({'error': 'Unauthorised.'}, status=status.HTTP_401_UNAUTHORIZED)


def _image_dimensions(uploaded):
    """Return (width, height) from raster bytes; SVG and unknown stay None."""
    content_type = (getattr(uploaded, 'content_type', '') or '').lower()
    if content_type == 'image/svg+xml':
        return None, None
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as img:
            width, height = img.size
        return width, height
    except (UnidentifiedImageError, OSError, ValueError):
        return None, None
    finally:
        try:
            uploaded.seek(0)
        except Exception:
            pass


class ImageListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    authentication_classes = []

    def get(self, request):
        qs = ImageAsset.objects.all()
        site = request.query_params.get('site', DEFAULT_SITE)
        if site:
            qs = qs.filter(site=site)
        slot = request.query_params.get('slot')
        if slot is not None and slot != '':
            qs = qs.filter(slot=slot)
        data = ImageAssetSerializer(qs, many=True, context={'request': request}).data
        return Response({'count': len(data), 'results': data})

    def post(self, request):
        denied = _admin_gate(request)
        if denied:
            return denied

        uploaded = request.FILES.get('file') or request.FILES.get('image')
        if uploaded is None:
            return Response(
                {'error': 'Multipart field "file" is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = (uploaded.content_type or '').lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {'error': f'Unsupported content type: {content_type or "unknown"}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        size = uploaded.size or 0
        if size > MAX_UPLOAD_BYTES:
            return Response(
                {'error': f'File too large. Max {MAX_UPLOAD_BYTES} bytes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        width, height = _image_dimensions(uploaded)

        sort_order = request.data.get('sort_order', 0)
        try:
            sort_order = int(sort_order)
        except (TypeError, ValueError):
            sort_order = 0

        asset = ImageAsset(
            title=request.data.get('title', '') or '',
            alt=request.data.get('alt', '') or '',
            content_type=content_type,
            size=size,
            width=width,
            height=height,
            sort_order=sort_order,
            slot=request.data.get('slot', '') or '',
            site=request.data.get('site', '') or DEFAULT_SITE,
        )
        # UUID is assigned on instantiation; FileField upload_to uses it.
        asset.file.save(uploaded.name, uploaded, save=False)
        asset.refresh_storage_fields()
        asset.save()

        logger.info('Arch image uploaded id=%s key=%s size=%s', asset.id, asset.storage_key, asset.size)
        return Response(
            ImageAssetSerializer(asset, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class ImageDetailView(APIView):
    authentication_classes = []

    def patch(self, request, pk):
        denied = _admin_gate(request)
        if denied:
            return denied
        asset = get_object_or_404(ImageAsset, pk=pk)
        serializer = ImageAssetPatchSerializer(asset, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ImageAssetSerializer(asset, context={'request': request}).data)

    def delete(self, request, pk):
        denied = _admin_gate(request)
        if denied:
            return denied
        asset = get_object_or_404(ImageAsset, pk=pk)
        asset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ImageReorderView(APIView):
    authentication_classes = []

    def put(self, request):
        denied = _admin_gate(request)
        if denied:
            return denied

        payload = request.data
        if not isinstance(payload, list):
            return Response(
                {'error': 'Body must be a JSON array of {id, sort_order, slot?}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReorderItemSerializer(data=payload, many=True)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data
        ids = [item['id'] for item in items]
        assets = {asset.id: asset for asset in ImageAsset.objects.filter(id__in=ids)}
        missing = [str(i) for i in ids if i not in assets]
        if missing:
            return Response(
                {'error': 'Unknown image ids.', 'ids': missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            for item in items:
                asset = assets[item['id']]
                asset.sort_order = item['sort_order']
                if 'slot' in item:
                    asset.slot = item['slot']
                update_fields = ['sort_order', 'updated_at']
                if 'slot' in item:
                    update_fields.append('slot')
                asset.save(update_fields=update_fields)

        qs = ImageAsset.objects.filter(id__in=ids)
        return Response({
            'count': qs.count(),
            'results': ImageAssetSerializer(qs, many=True, context={'request': request}).data,
        })


class ChromeView(APIView):
    authentication_classes = []

    def get(self, request):
        site = request.query_params.get('site', DEFAULT_SITE) or DEFAULT_SITE
        chrome, _ = SiteChrome.objects.get_or_create(site=site, defaults={'data': {}})
        return Response(SiteChromeSerializer(chrome).data)

    def put(self, request):
        denied = _admin_gate(request)
        if denied:
            return denied
        site = request.query_params.get('site', DEFAULT_SITE) or DEFAULT_SITE
        body = request.data
        if not isinstance(body, dict):
            return Response(
                {'error': 'Body must be a JSON object (the chrome document).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if set(body.keys()) <= {'chrome', 'data', 'site'} and (
            'chrome' in body or 'data' in body
        ):
            document = body.get('chrome', body.get('data'))
            if not isinstance(document, dict):
                return Response(
                    {'error': 'chrome/data must be a JSON object.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            document = body

        chrome, _ = SiteChrome.objects.update_or_create(
            site=site,
            defaults={'data': document},
        )
        return Response(SiteChromeSerializer(chrome).data)
