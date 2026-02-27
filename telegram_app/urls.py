from django.urls import path
from telegram_app import views

urlpatterns = [
    path('webhook/', views.webhook, name='telegram_webhook'),
    path('auth/', views.telegram_auth, name='telegram_auth'),
]
