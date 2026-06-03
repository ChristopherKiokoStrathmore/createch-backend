from django.urls import path
from .views import MpesaCallbackView, PaymentStatusView

urlpatterns = [
    path('callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
    path('status/<uuid:order_id>/', PaymentStatusView.as_view(), name='mpesa-payment-status'),
]
