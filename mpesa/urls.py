from django.urls import path
from .views import MpesaCallbackView

urlpatterns = [
    path('callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
]
