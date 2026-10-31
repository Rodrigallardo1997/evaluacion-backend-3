"""
URLs para la API de usuarios y autenticación.
"""
from django.urls import path
from apps.usuarios.api_views import LoginAPIView, LogoutAPIView, MeAPIView

app_name = "api-usuarios"

urlpatterns = [
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    path("auth/me/", MeAPIView.as_view(), name="me"),
]
