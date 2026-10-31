"""
Servicios de dominio para logística y rutas de despacho.
"""
from apps.despachos.services.despacho_service import (
    iniciar_ruta,
    confirmar_entrega,
    registrar_entrega_fallida,
    agregar_parada_ruta,
    cerrar_ruta,
)

__all__ = [
    "iniciar_ruta",
    "confirmar_entrega",
    "registrar_entrega_fallida",
    "agregar_parada_ruta",
    "cerrar_ruta",
]
