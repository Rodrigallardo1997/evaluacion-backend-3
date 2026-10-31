"""
Servicios de dominio para inventario.
"""
from apps.inventario.services.stock_service import (
    calcular_consumo_pedido,
    descontar_stock_pedido,
    reintegrar_stock_pedido,
    registrar_movimiento,
)

__all__ = [
    "calcular_consumo_pedido",
    "descontar_stock_pedido",
    "reintegrar_stock_pedido",
    "registrar_movimiento",
]
