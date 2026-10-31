"""
Modelos de la app despachos: RutaDespacho, Despacho.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class RutaDespacho(models.Model):
    """
    Ruta de despacho que agrupa varios pedidos asignados a un repartidor.
    """

    class Estado(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        EN_RUTA = "EN_RUTA", "En Ruta"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    codigo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        verbose_name="código",
        db_index=True,
    )
    fecha = models.DateField(
        verbose_name="fecha",
        db_index=True,
    )
    repartidor = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="rutas",
        verbose_name="repartidor",
    )
    vehiculo = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="vehículo",
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PLANIFICADA,
        verbose_name="estado",
        db_index=True,
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="observaciones",
    )
    creado_por = models.ForeignKey(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rutas_creadas",
        verbose_name="creado por",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="creado en",
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name="actualizado en",
    )

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def total_paradas(self) -> int:
        """Total de paradas (despachos) en la ruta."""
        return self.paradas.count()

    @property
    def entregadas(self) -> int:
        """Cantidad de paradas entregadas."""
        return self.paradas.filter(estado=Despacho.Estado.ENTREGADO).count()

    @property
    def pendientes(self) -> int:
        """Cantidad de paradas pendientes."""
        return self.paradas.filter(estado=Despacho.Estado.PENDIENTE).count()

    @property
    def esta_completa(self) -> bool:
        """True si todas las paradas están entregadas o fallidas."""
        return (
            self.total_paradas > 0
            and self.paradas.filter(estado=Despacho.Estado.PENDIENTE).count() == 0
        )

    # ------------------------------------------------------------------
    # Métodos de negocio
    # ------------------------------------------------------------------

    def generar_codigo(self) -> str:
        """
        Genera el código con formato RUTA-AAAA-NNNN usando el pk.
        Asigna y guarda directamente el campo codigo.
        """
        año = self.fecha.year if self.fecha else timezone.now().year
        codigo = f"RUTA-{año}-{self.pk:04d}"
        self.codigo = codigo
        RutaDespacho.objects.filter(pk=self.pk).update(codigo=codigo)
        return codigo

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.codigo or f'Ruta #{self.pk}'} - {self.fecha} ({self.repartidor})"

    class Meta:
        verbose_name = "ruta de despacho"
        verbose_name_plural = "rutas de despacho"
        ordering = ["-fecha"]


class Despacho(models.Model):
    """
    Parada individual dentro de una ruta de despacho.
    Representa la entrega de un pedido específico.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ENTREGADO = "ENTREGADO", "Entregado"
        FALLIDO = "FALLIDO", "Fallido"

    ruta = models.ForeignKey(
        RutaDespacho,
        on_delete=models.CASCADE,
        related_name="paradas",
        verbose_name="ruta",
    )
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        on_delete=models.CASCADE,
        related_name="despachos",
        verbose_name="pedido",
    )
    orden = models.PositiveIntegerField(
        verbose_name="orden",
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name="estado",
    )
    receptor_nombre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="nombre del receptor",
    )
    firma_digital = models.TextField(
        blank=True,
        verbose_name="firma digital",
    )
    foto_comprobante = models.ImageField(
        upload_to="comprobantes/",
        null=True,
        blank=True,
        verbose_name="foto comprobante",
    )
    fecha_entrega = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="fecha de entrega",
    )
    latitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="latitud",
    )
    longitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="longitud",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="observaciones",
    )

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def clean(self):
        # Solo validar al crear (pk es None)
        if self.pk is None and self.pedido_id:
            from apps.pedidos.models import Pedido as PedidoModel
            try:
                pedido = PedidoModel.objects.get(pk=self.pedido_id)
                if pedido.estado != PedidoModel.Estado.LISTO:
                    raise ValidationError(
                        {"pedido": "El pedido debe estar en estado LISTO para crear un despacho."}
                    )
            except PedidoModel.DoesNotExist:
                pass

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"Parada #{self.orden} | {self.ruta} | {self.pedido}"

    class Meta:
        verbose_name = "despacho"
        verbose_name_plural = "despachos"
        ordering = ["ruta", "orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruta", "orden"],
                name="despacho_ruta_orden_unique",
            )
        ]
