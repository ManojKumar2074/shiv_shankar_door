from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('gallery/', views.gallery, name='gallery'),
    path('door/<int:pk>/', views.door_detail, name='door_detail'),
    path('ai-preview/', views.ai_preview, name='ai_preview'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
