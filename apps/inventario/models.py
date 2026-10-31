"""
Modelos de la app inventario: MovimientoInventario.
"""
from decimal import Decimal

from django.db import models


class MovimientoInventario(models.Model):
    """
    Registro de cada movimiento de stock de un insumo.
    Permite trazabilidad completa del inventario.
    """

    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        AJUSTE = "AJUSTE", "Ajuste"
        MERMA = "MERMA", "Merma"

    insumo = models.ForeignKey(
        "catalogo.Insumo",
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name="insumo",
    )
    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        verbose_name="tipo de movimiento",
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name="cantidad",
    )
    stock_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="stock anterior",
    )
    stock_nuevo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="stock nuevo",
    )
    motivo = models.CharField(
        max_length=200,
        verbose_name="motivo",
    )
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movimientos_inventario",
        verbose_name="pedido",
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movimientos_inventario",
        verbose_name="usuario",
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="fecha",
    )

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"{self.get_tipo_display()} | {self.insumo} | "
            f"{self.cantidad} ({self.stock_anterior} → {self.stock_nuevo})"
        )

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-fecha"]
