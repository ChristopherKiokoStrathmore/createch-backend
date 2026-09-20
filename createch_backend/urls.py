from django.conf import settings
from django.contrib import admin
from django.http import Http404, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve as static_serve


def health(request):
    return JsonResponse({'status': 'ok'})


def serve_media(request, path):
    """Serve MEDIA_ROOT. Used in DEBUG and when SERVE_MEDIA=True (Railway volume)."""
    if settings.USE_S3_MEDIA or not (settings.DEBUG or settings.SERVE_MEDIA):
        raise Http404()
    return static_serve(request, path, document_root=str(settings.MEDIA_ROOT))


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health),
    path('api/arch/', include('arch_media.urls')),
    path('api/', include('orders.urls')),
    re_path(r'^media/(?P<path>.*)$', serve_media),
]
