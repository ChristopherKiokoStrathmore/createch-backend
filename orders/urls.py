from django.urls import path
from . import views

urlpatterns = [
    path('orders/',                   views.OrderView.as_view(),       name='orders'),
    path('orders/<uuid:order_id>/',   views.OrderDetailView.as_view(), name='order-detail'),
]
