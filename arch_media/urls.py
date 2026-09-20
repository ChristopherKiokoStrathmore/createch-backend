from django.urls import path

from . import views

urlpatterns = [
    path('images/reorder/', views.ImageReorderView.as_view(), name='arch-images-reorder'),
    path('images/', views.ImageListCreateView.as_view(), name='arch-images'),
    path('images/<uuid:pk>/', views.ImageDetailView.as_view(), name='arch-image-detail'),
    path('chrome/', views.ChromeView.as_view(), name='arch-chrome'),
]
