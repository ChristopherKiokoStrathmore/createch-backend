from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health),
    path('api/', include('orders.urls')),
    path('api/mpesa/', include('mpesa.urls')),
    path('api/intasend/', include('intasend_app.urls')),
]
