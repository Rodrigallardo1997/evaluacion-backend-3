"""
Modelos de la app catálogo: Insumo, Receta, RecetaInsumo.
"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Insumo(models.Model):
    """
    Materia prima o insumo utilizado en la producción de recetas.
    """

    class Categoria(models.TextChoices):
        HARINAS = "HARINAS", "Harinas"
        LACTEOS = "LACTEOS", "Lácteos"
        HUEVOS = "HUEVOS", "Huevos"
        AZUCARES = "AZUCARES", "Azúcares"
        CHOCOLATES = "CHOCOLATES", "Chocolates"
        FRUTAS = "FRUTAS", "Frutas"
        DECORACION = "DECORACION", "Decoración"
        OTROS = "OTROS", "Otros"

    class Unidad(models.TextChoices):
        KG = "KG", "Kilogramo"
        G = "G", "Gramo"
        L = "L", "Litro"
        ML = "ML", "Mililitro"
        UNIDAD = "UNIDAD", "Unidad"

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="nombre",
        db_index=True,
    )
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        verbose_name="categoría",
        db_index=True,
    )
    unidad = models.CharField(
        max_length=10,
        choices=Unidad.choices,
        verbose_name="unidad de medida",
    )
    stock_actual = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        verbose_name="stock actual",
    )
    stock_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        verbose_name="stock mínimo",
    )
    costo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="costo unitario",
    )
    perecedero = models.BooleanField(
        default=False,
        verbose_name="perecedero",
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name="fecha de vencimiento",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="activo",
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
    def stock_bajo(self) -> bool:
        """Retorna True si el stock actual está por debajo o igual al mínimo."""
        return self.stock_actual <= self.stock_minimo

    @property
    def valor_inventario(self) -> Decimal:
        """Retorna el valor total del inventario (stock × costo unitario)."""
        return self.stock_actual * self.costo_unitario

    @property
    def esta_vencido(self) -> bool:
        """Retorna True si el insumo tiene fecha de vencimiento y ya venció."""
        if self.fecha_vencimiento is None:
            return False
        return self.fecha_vencimiento < timezone.localdate()

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_unidad_display()})"

    class Meta:
        verbose_name = "insumo"
        verbose_name_plural = "insumos"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(stock_actual__gte=0),
                name="insumo_stock_actual_no_negativo",
            )
        ]


class Receta(models.Model):
    """
    Receta de producción de Dulce Arte.
    Define los insumos necesarios y parámetros de costos y precios.
    """

    class Categoria(models.TextChoices):
        TORTA = "TORTA", "Torta"
        POSTRE = "POSTRE", "Postre"
        GALLETA = "GALLETA", "Galleta"
        PAN = "PAN", "Pan"
        DULCE = "DULCE", "Dulces & Pastelería"
        CAFETERIA = "CAFETERIA", "Cafetería & Bebidas"
        OTRO = "OTRO", "Otro"

    nombre = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="nombre",
        db_index=True,
    )
    descripcion = models.TextField(
        verbose_name="descripción",
    )
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        verbose_name="categoría",
    )
    rendimiento = models.PositiveIntegerField(
        default=1,
        verbose_name="rendimiento (unidades)",
    )
    precio_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="precio base",
    )
    margen_deseado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("30"),
        verbose_name="margen deseado (%)",
    )
    tiempo_preparacion_min = models.PositiveIntegerField(
        default=60,
        verbose_name="tiempo de preparación (min)",
    )
    imagen = models.ImageField(
        upload_to="recetas/",
        null=True,
        blank=True,
        verbose_name="imagen",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="activo",
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
    def costo_insumos(self) -> Decimal:
        """
        Costo total de todos los insumos de la receta
        (incluyendo merma).
        """
        total = Decimal("0")
        for ri in self.insumos.select_related("insumo").all():
            total += ri.cantidad_neta * ri.insumo.costo_unitario
        return total

    @property
    def costo_unitario_produccion(self) -> Decimal:
        """Costo por unidad producida según el rendimiento."""
        if self.rendimiento and self.rendimiento > 0:
            return self.costo_insumos / Decimal(self.rendimiento)
        return Decimal("0")

    @property
    def margen_real(self) -> Decimal:
        """
        Margen real expresado en porcentaje respecto al precio_base.
        Retorna 0 si precio_base es 0.
        """
        if not self.precio_base or self.precio_base == Decimal("0"):
            return Decimal("0")
        return (
            (self.precio_base - self.costo_unitario_produccion) / self.precio_base
        ) * Decimal("100")

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def clean(self):
        errors = {}
        if self.rendimiento is not None and self.rendimiento <= 0:
            errors["rendimiento"] = "El rendimiento debe ser mayor a 0."
        if self.precio_base is not None and self.precio_base < Decimal("0"):
            errors["precio_base"] = "El precio base no puede ser negativo."
        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.nombre} ({self.get_categoria_display()})"

    class Meta:
        verbose_name = "receta"
        verbose_name_plural = "recetas"
        ordering = ["nombre"]


class RecetaInsumo(models.Model):
    """
    Relación entre Receta e Insumo con cantidad y porcentaje de merma.
    """

    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name="insumos",
        verbose_name="receta",
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.CASCADE,
        related_name="recetas",
        verbose_name="insumo",
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name="cantidad",
    )
    merma_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="merma (%)",
    )

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def cantidad_neta(self) -> Decimal:
        """Cantidad real utilizada considerando merma."""
        return self.cantidad * (1 + self.merma_porcentaje / Decimal("100"))

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def clean(self):
        errors = {}
        if self.cantidad is not None and self.cantidad <= Decimal("0"):
            errors["cantidad"] = "La cantidad debe ser mayor a 0."
        if self.merma_porcentaje is not None:
            if self.merma_porcentaje < Decimal("0") or self.merma_porcentaje > Decimal("100"):
                errors["merma_porcentaje"] = "La merma debe estar entre 0 y 100."
        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.receta} → {self.insumo} ({self.cantidad} {self.insumo.get_unidad_display()})"

    class Meta:
        verbose_name = "insumo de receta"
        verbose_name_plural = "insumos de receta"
        constraints = [
            models.UniqueConstraint(
                fields=["receta", "insumo"],
                name="recetainsumo_receta_insumo_unique",
            )
        ]
