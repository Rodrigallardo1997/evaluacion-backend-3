"""
Modelos de la app usuarios.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Usuario personalizado del sistema Dulce Arte.
    Extiende AbstractUser agregando rol y teléfono.
    """

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        VENDEDOR = "VENDEDOR", "Vendedor"
        COCINA = "COCINA", "Cocina"
        REPARTIDOR = "REPARTIDOR", "Repartidor"
        CLIENTE = "CLIENTE", "Cliente"

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.VENDEDOR,
        verbose_name="rol",
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="teléfono",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name="creado en",
    )

    # ------------------------------------------------------------------
    # Propiedades de conveniencia
    # ------------------------------------------------------------------

    @property
    def es_admin(self) -> bool:
        """Retorna True si el usuario tiene rol ADMIN."""
        return self.rol == self.Rol.ADMIN

    @property
    def es_vendedor(self) -> bool:
        """Retorna True si el usuario tiene rol VENDEDOR."""
        return self.rol == self.Rol.VENDEDOR

    @property
    def es_cocina(self) -> bool:
        """Retorna True si el usuario tiene rol COCINA."""
        return self.rol == self.Rol.COCINA

    @property
    def es_repartidor(self) -> bool:
        """Retorna True si el usuario tiene rol REPARTIDOR."""
        return self.rol == self.Rol.REPARTIDOR

    @property
    def es_cliente(self) -> bool:
        """Retorna True si el usuario tiene rol CLIENTE."""
        return self.rol == self.Rol.CLIENTE

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-creado_en"]
