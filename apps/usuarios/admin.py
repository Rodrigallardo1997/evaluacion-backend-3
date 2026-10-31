"""
Personalización del Django Admin para Usuarios.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "rol",
        "telefono",
        "is_staff",
        "is_active",
        "creado_en",
    ]
    list_filter = ["rol", "is_staff", "is_active", "creado_en"]
    search_fields = ["username", "first_name", "last_name", "email", "telefono"]
    ordering = ["-creado_en"]
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Información personal"), {"fields": ("first_name", "last_name", "email", "telefono")}),
        (
            _("Rol y Permisos"),
            {
                "fields": (
                    "rol",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Fechas importantes"), {"fields": ("last_login", "date_joined")}),
    )

    def has_module_permission(self, request):
        # Solo admin y superuser acceden al módulo de usuarios
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.es_admin

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.es_admin

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.es_admin

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.es_admin
