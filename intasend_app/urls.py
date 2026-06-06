from django.urls import path
from .views import IntaSendWebhookView

urlpatterns = [
    path("webhook/", IntaSendWebhookView.as_view(), name="intasend-webhook"),
]
