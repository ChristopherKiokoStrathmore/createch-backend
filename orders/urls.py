from django.urls import path
from . import views
from .webhooks import WooWebhookView

urlpatterns = [
    path('orders/',                   views.OrderView.as_view(),          name='orders'),
    path('orders/<uuid:order_id>/',   views.OrderDetailView.as_view(),    name='order-detail'),
    path('payment/status/',           views.PaymentStatusView.as_view(),  name='payment-status'),
    path('woo/webhook/',              WooWebhookView.as_view(),           name='woo-webhook'),
]
