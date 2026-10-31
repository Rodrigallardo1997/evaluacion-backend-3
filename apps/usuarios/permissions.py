"""
Permisos y autorización por roles para vistas web y Django REST Framework.
"""
from functools import wraps
from typing import List, Tuple

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from rest_framework import permissions


class RoleRequiredMixin(AccessMixin):
    """
    Mixin para CBVs de Django que restringe el acceso según roles.
    roles_required = ['ADMIN', 'VENDEDOR']
    """
    roles_required: List[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if self.roles_required and request.user.rol not in self.roles_required:
            raise PermissionDenied("No tienes permisos suficientes para acceder a esta sección.")

        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    """
    Decorador para FBVs de Django que restringe el acceso según roles.
    @role_required('ADMIN', 'COCINA')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if roles and request.user.rol not in roles:
                raise PermissionDenied("No tienes permisos suficientes para realizar esta acción.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class RolePermission(permissions.BasePermission):
    """
    Permiso para ViewSets de DRF que mapea acciones a listas de roles permitidos.

    Ejemplo en ViewSet:
    role_action_map = {
        'list': ['ADMIN', 'VENDEDOR', 'COCINA'],
        'create': ['ADMIN', 'VENDEDOR'],
        'retrieve': ['ADMIN', 'VENDEDOR', 'COCINA'],
        'update': ['ADMIN'],
        'destroy': ['ADMIN'],
    }
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        role_map = getattr(view, "role_action_map", None)
        if not role_map:
            # Si no hay mapeo específico, permitir autenticados
            return True

        action = getattr(view, "action", request.method.lower())
        allowed_roles = role_map.get(action, role_map.get("default", []))

        if not allowed_roles:
            return True

        return request.user.rol in allowed_roles

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.es_admin:
            return True

        # Permisos a nivel de objeto para cliente
        if request.user.es_cliente:
            # En pedido
            if hasattr(obj, "cliente") and hasattr(obj.cliente, "usuario"):
                return obj.cliente.usuario == request.user
            # En cliente
            if hasattr(obj, "usuario"):
                return obj.usuario == request.user
            # En cotización o pago
            if hasattr(obj, "pedido") and hasattr(obj.pedido.cliente, "usuario"):
                return obj.pedido.cliente.usuario == request.user
            return False

        # Permisos a nivel de objeto para repartidor
        if request.user.es_repartidor:
            if hasattr(obj, "repartidor"):
                return obj.repartidor == request.user
            if hasattr(obj, "ruta") and hasattr(obj.ruta, "repartidor"):
                return obj.ruta.repartidor == request.user
            return True

        return True
