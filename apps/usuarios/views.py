"""
Vistas web para usuarios y redirecciones de conveniencia.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def index(request):
    """Redirige al listado de clientes."""
    return redirect("pedidos:clientes")
