"""
Modelos de la app pedidos:
Cliente, Pedido, DetallePedido, Cotizacion, HistorialEstadoPedido, Pago.
"""
import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    """
    Cliente de Dulce Arte. Puede estar vinculado a un Usuario del sistema.
    """

    nombre_completo = models.CharField(
        max_length=150,
        verbose_name="nombre completo",
    )
    rut = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        verbose_name="RUT",
    )
    telefono = models.CharField(
        max_length=20,
        verbose_name="teléfono",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="correo electrónico",
    )
    direccion = models.TextField(
        verbose_name="dirección",
    )
    referencia_direccion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="referencia de dirección",
    )
    notas = models.TextField(
        blank=True,
        verbose_name="notas",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="activo",
    )
    usuario = models.OneToOneField(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cliente",
        verbose_name="usuario",
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
    # Validación
    # ------------------------------------------------------------------

    def _validar_rut(self, rut: str) -> bool:
        """Valida formato chileno simple: XX.XXX.XXX-X o XXXXXXXX-X."""
        patron = r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$"
        return bool(re.match(patron, rut.strip()))

    def clean(self):
        errors = {}
        if not self.telefono and not self.email:
            errors["telefono"] = "Debe proporcionar al menos teléfono o correo electrónico."
        if self.rut:
            if not self._validar_rut(self.rut):
                errors["rut"] = "Formato de RUT inválido. Ejemplo: 12.345.678-9"
        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return self.nombre_completo

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre_completo"]


class Pedido(models.Model):
    """
    Pedido principal del sistema Dulce Arte.
    Gestiona el ciclo de vida completo desde cotización hasta entrega.
    """

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        COTIZADO = "COTIZADO", "Cotizado"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        EN_PREPARACION = "EN_PREPARACION", "En Preparación"
        HORNEADO_DECORADO = "HORNEADO_DECORADO", "Horneado/Decorado"
        CONTROL_CALIDAD = "CONTROL_CALIDAD", "Control de Calidad"
        LISTO = "LISTO", "Listo"
        EN_DESPACHO = "EN_DESPACHO", "En Despacho"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    # Mapeo de estado a columna kanban (5 columnas exactas de cocina)
    _KANBAN_MAP = {
        Estado.CONFIRMADO: "recibido",
        Estado.EN_PREPARACION: "en_preparacion",
        Estado.HORNEADO_DECORADO: "horneado",
        Estado.CONTROL_CALIDAD: "calidad",
        Estado.LISTO: "listo",
    }

    # Estados que permiten edición (solo BORRADOR según especificación)
    _ESTADOS_EDITABLES = {
        Estado.BORRADOR,
    }

    codigo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        verbose_name="código",
        db_index=True,
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="pedidos",
        verbose_name="cliente",
    )
    vendedor = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pedidos_vendidos",
        verbose_name="vendedor",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        verbose_name="estado",
        db_index=True,
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        verbose_name="prioridad",
    )
    fecha_entrega = models.DateTimeField(
        verbose_name="fecha de entrega",
        db_index=True,
    )
    direccion_entrega = models.TextField(
        verbose_name="dirección de entrega",
    )
    diseno_descripcion = models.TextField(
        verbose_name="descripción del diseño",
    )
    imagen_referencia = models.ImageField(
        upload_to="pedidos/",
        null=True,
        blank=True,
        verbose_name="imagen de referencia",
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="observaciones",
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="subtotal",
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="descuento",
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="total",
    )
    anticipo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="anticipo",
    )
    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="saldo",
    )
    inventario_descontado = models.BooleanField(
        default=False,
        verbose_name="inventario descontado",
    )
    version = models.PositiveIntegerField(
        default=0,
        verbose_name="versión",
    )
    fecha_entrega_real = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="fecha de entrega real",
    )
    motivo_cancelacion = models.TextField(
        blank=True,
        verbose_name="motivo de cancelación",
    )
    cancelado_por = models.ForeignKey(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_cancelados",
        verbose_name="cancelado por",
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
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def columna_kanban(self) -> str:
        """Retorna la columna kanban correspondiente al estado actual (o vacío si no está en cocina)."""
        return self._KANBAN_MAP.get(self.estado, "")

    @property
    def cotizacion_actual(self):
        """Retorna la cotización VIGENTE más reciente del pedido."""
        return self.cotizaciones.filter(estado="VIGENTE").order_by("-fecha_emision").first()

    # ------------------------------------------------------------------
    # Métodos de negocio
    # ------------------------------------------------------------------

    def generar_codigo(self) -> str:
        """
        Genera el código con formato DA-AAAA-NNNN usando el pk del pedido.
        Lo asigna directamente al campo codigo y guarda (solo el campo codigo).
        """
        anio = timezone.now().year
        codigo = f"DA-{anio}-{self.pk:04d}"
        self.codigo = codigo
        Pedido.objects.filter(pk=self.pk).update(codigo=codigo)
        return codigo

    def recalcular_totales(self) -> None:
        """
        Recalcula subtotal, total y saldo a partir de los detalles y pagos.
        - subtotal = suma de detalles
        - total = subtotal - descuento
        - anticipo = suma de pagos tipo ANTICIPO
        - saldo = total - suma de todos los pagos
        """
        subtotal = Decimal("0")
        for detalle in self.detalles.all():
            subtotal += detalle.subtotal

        self.subtotal = subtotal
        self.total = max(subtotal - self.descuento, Decimal("0"))

        pagos_anticipo = Decimal("0")
        pagos_total = Decimal("0")
        for pago in self.pagos.all():
            pagos_total += pago.monto
            if pago.tipo == Pago.Tipo.ANTICIPO:
                pagos_anticipo += pago.monto

        self.anticipo = pagos_anticipo
        self.saldo = max(self.total - pagos_total, Decimal("0"))

    def puede_editarse(self) -> bool:
        """Retorna True si el pedido está en un estado editable."""
        return self.estado in self._ESTADOS_EDITABLES

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def clean(self):
        errors = {}
        if self.descuento is not None and self.subtotal is not None:
            if self.descuento > self.subtotal:
                errors["descuento"] = "El descuento no puede superar el subtotal."
        if self.anticipo is not None and self.total is not None:
            if self.anticipo > self.total:
                errors["anticipo"] = "El anticipo no puede superar el total."
        if self.saldo is not None and self.saldo < Decimal("0"):
            errors["saldo"] = "El saldo no puede ser negativo."
        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.codigo or f'Pedido #{self.pk}'} - {self.cliente}"

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-creado_en"]


class DetallePedido(models.Model):
    """
    Línea de detalle de un pedido con receta, cantidad y precio.
    """

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="pedido",
    )
    receta = models.ForeignKey(
        "catalogo.Receta",
        on_delete=models.PROTECT,
        verbose_name="receta",
    )
    cantidad = models.PositiveIntegerField(
        verbose_name="cantidad",
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="precio unitario",
    )
    personalizacion = models.TextField(
        blank=True,
        verbose_name="personalización",
    )

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def subtotal(self) -> Decimal:
        """Subtotal = cantidad × precio unitario."""
        return Decimal(self.cantidad) * self.precio_unitario

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def clean(self):
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor a 0."})

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.receta} × {self.cantidad} (Pedido {self.pedido})"

    class Meta:
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"


class Cotizacion(models.Model):
    """
    Cotización formal asociada a un pedido.
    """

    class Estado(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        ACEPTADA = "ACEPTADA", "Aceptada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        VENCIDA = "VENCIDA", "Vencida"

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="cotizaciones",
        verbose_name="pedido",
    )
    numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="número",
    )
    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        verbose_name="fecha de emisión",
    )
    valida_hasta = models.DateField(
        verbose_name="válida hasta",
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="subtotal",
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="descuento",
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="total",
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.VIGENTE,
        verbose_name="estado",
    )
    condiciones = models.TextField(
        blank=True,
        verbose_name="condiciones",
    )
    creado_por = models.ForeignKey(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cotizaciones_creadas",
        verbose_name="creado por",
    )

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def esta_vigente(self) -> bool:
        """Retorna True si la cotización está vigente y no ha vencido."""
        return (
            self.estado == self.Estado.VIGENTE
            and self.valida_hasta >= timezone.localdate()
        )

    # ------------------------------------------------------------------
    # Métodos de negocio
    # ------------------------------------------------------------------

    def aceptar(self, usuario) -> None:
        """Marca la cotización como aceptada."""
        self.estado = self.Estado.ACEPTADA
        self.save(update_fields=["estado"])

    def rechazar(self, usuario) -> None:
        """Marca la cotización como rechazada."""
        self.estado = self.Estado.RECHAZADA
        self.save(update_fields=["estado"])

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"Cotización {self.numero} ({self.get_estado_display()})"

    class Meta:
        verbose_name = "cotización"
        verbose_name_plural = "cotizaciones"
        ordering = ["-fecha_emision"]


class HistorialEstadoPedido(models.Model):
    """
    Registro histórico de cambios de estado en un pedido.
    """

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="historial",
        verbose_name="pedido",
    )
    estado_anterior = models.CharField(
        max_length=20,
        choices=Pedido.Estado.choices,
        verbose_name="estado anterior",
    )
    estado_nuevo = models.CharField(
        max_length=20,
        choices=Pedido.Estado.choices,
        verbose_name="estado nuevo",
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cambios_estado",
        verbose_name="usuario",
    )
    observacion = models.TextField(
        blank=True,
        verbose_name="observación",
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
            f"{self.pedido} | {self.estado_anterior} → {self.estado_nuevo}"
        )

    class Meta:
        verbose_name = "historial de estado"
        verbose_name_plural = "historial de estados"
        ordering = ["fecha"]


class Pago(models.Model):
    """
    Registro de pago asociado a un pedido.
    """

    class Tipo(models.TextChoices):
        ANTICIPO = "ANTICIPO", "Anticipo"
        ABONO = "ABONO", "Abono"
        SALDO = "SALDO", "Saldo"

    class Metodo(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        DEBITO = "DEBITO", "Débito"
        CREDITO = "CREDITO", "Crédito"

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="pagos",
        verbose_name="pedido",
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="monto",
    )
    tipo = models.CharField(
        max_length=15,
        choices=Tipo.choices,
        verbose_name="tipo",
    )
    metodo = models.CharField(
        max_length=15,
        choices=Metodo.choices,
        verbose_name="método de pago",
    )
    referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="referencia",
    )
    comprobante = models.ImageField(
        upload_to="comprobantes_pago/",
        null=True,
        blank=True,
        verbose_name="comprobante",
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="fecha",
    )
    registrado_por = models.ForeignKey(
        "usuarios.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pagos_registrados",
        verbose_name="registrado por",
    )

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def clean(self):
        if self.monto is not None and self.monto <= Decimal("0"):
            raise ValidationError({"monto": "El monto debe ser mayor a 0."})

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"Pago ${self.monto} ({self.get_tipo_display()}) - {self.pedido}"

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["-fecha"]
