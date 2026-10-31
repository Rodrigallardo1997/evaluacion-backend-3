"""
Pruebas automatizadas del sistema Dulce Arte.
Cubre las 15 pruebas obligatorias de la rúbrica más pruebas de humo de endpoints.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalogo.models import Insumo, Receta, RecetaInsumo
from apps.despachos.models import RutaDespacho, Despacho
from apps.despachos.services.despacho_service import (
    iniciar_ruta,
    confirmar_entrega,
)
from apps.inventario.models import MovimientoInventario
from apps.inventario.services.stock_service import (
    descontar_stock_pedido,
    reintegrar_stock_pedido,
)
from apps.pedidos.models import (
    Cliente,
    Pedido,
    DetallePedido,
    Cotizacion,
    HistorialEstadoPedido,
    Pago,
)
from apps.pedidos.services.cotizacion_service import (
    emitir_cotizacion,
    confirmar_pedido,
    cancelar_pedido,
    transicionar_estado,
    ConflictError,
)
from apps.usuarios.models import Usuario


class DulceArteBaseTestCase(TestCase):
    """Configuración base para todas las pruebas con usuarios y datos maestros."""

    def setUp(self):
        # Usuarios por rol
        self.admin = Usuario.objects.create_user(
            username="admin_test", password="Password123!", rol=Usuario.Rol.ADMIN, is_staff=True, is_superuser=True
        )
        self.vendedor = Usuario.objects.create_user(
            username="vendedor_test", password="Password123!", rol=Usuario.Rol.VENDEDOR, is_staff=True
        )
        self.cocina = Usuario.objects.create_user(
            username="cocina_test", password="Password123!", rol=Usuario.Rol.COCINA, is_staff=True
        )
        self.repartidor = Usuario.objects.create_user(
            username="repartidor_test", password="Password123!", rol=Usuario.Rol.REPARTIDOR, is_staff=True
        )
        self.usuario_cliente = Usuario.objects.create_user(
            username="cliente_test", password="Password123!", rol=Usuario.Rol.CLIENTE
        )

        # Clientes
        self.cliente = Cliente.objects.create(
            nombre_completo="Cliente Prueba 1",
            rut="12.345.678-9",
            telefono="+56 9 1111 2222",
            email="cliente1@test.cl",
            direccion="Av. Siempre Viva 742, Providencia",
            usuario=self.usuario_cliente,
        )
        self.otro_cliente = Cliente.objects.create(
            nombre_completo="Cliente Prueba 2",
            rut="18.765.432-1",
            telefono="+56 9 3333 4444",
            email="cliente2@test.cl",
            direccion="Calle Moneda 100, Santiago",
        )

        # Insumos
        self.insumo_harina = Insumo.objects.create(
            nombre="Harina Especial Test",
            categoria=Insumo.Categoria.HARINAS,
            unidad=Insumo.Unidad.KG,
            stock_actual=Decimal("10.000"),
            stock_minimo=Decimal("2.000"),
            costo_unitario=Decimal("1000.00"),
        )
        self.insumo_chocolate = Insumo.objects.create(
            nombre="Chocolate Belga Test",
            categoria=Insumo.Categoria.CHOCOLATES,
            unidad=Insumo.Unidad.KG,
            stock_actual=Decimal("5.000"),
            stock_minimo=Decimal("3.000"),
            costo_unitario=Decimal("10000.00"),
        )

        # Receta con BOM y merma del 5%
        self.receta_torta = Receta.objects.create(
            nombre="Torta Trufa Test",
            categoria=Receta.Categoria.TORTA,
            descripcion="Torta para tests",
            rendimiento=1,
            precio_base=Decimal("25000.00"),
            margen_deseado=Decimal("30"),
            tiempo_preparacion_min=60,
        )
        # 1 kg de harina con 5% de merma = 1.050 kg netos
        RecetaInsumo.objects.create(
            receta=self.receta_torta,
            insumo=self.insumo_harina,
            cantidad=Decimal("1.000"),
            merma_porcentaje=Decimal("5.00"),
        )
        # 0.5 kg de chocolate sin merma = 0.500 kg netos
        RecetaInsumo.objects.create(
            receta=self.receta_torta,
            insumo=self.insumo_chocolate,
            cantidad=Decimal("0.500"),
            merma_porcentaje=Decimal("0.00"),
        )

        # Cliente DRF
        self.api_client = APIClient()


class ReglasNegocioTests(DulceArteBaseTestCase):
    """Pruebas de lógica de dominio (BOM, stock, cotizaciones, Kanban y logística)."""

    def test_01_confirmar_pedido_descuenta_stock_con_merma(self):
        """Prueba 1: Verifica cantidades exactas descontadas con merma y movimientos SALIDA."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            receta=self.receta_torta,
            cantidad=2, # Requiere: Harina = 2 * 1.05 = 2.100 kg; Chocolate = 2 * 0.5 = 1.000 kg
            precio_unitario=self.receta_torta.precio_base,
        )
        pedido.recalcular_totales()
        pedido.save()

        emitir_cotizacion(pedido.id, self.vendedor)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.COTIZADO)

        # Confirmar
        confirmar_pedido(pedido.id, self.vendedor)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.CONFIRMADO)
        self.assertTrue(pedido.inventario_descontado)

        # Verificar stock descontado
        self.insumo_harina.refresh_from_db()
        self.insumo_chocolate.refresh_from_db()
        # Inicial 10.000 - 2.100 = 7.900
        self.assertEqual(self.insumo_harina.stock_actual, Decimal("7.900"))
        # Inicial 5.000 - 1.000 = 4.000
        self.assertEqual(self.insumo_chocolate.stock_actual, Decimal("4.000"))

        # Verificar movimientos SALIDA registrados
        movs = MovimientoInventario.objects.filter(pedido=pedido, tipo=MovimientoInventario.Tipo.SALIDA)
        self.assertEqual(movs.count(), 2)

    def test_02_confirmar_sin_stock_no_modifica_nada(self):
        """Prueba 2: Rollback total cuando falta stock, sin movimientos ni cambios."""
        # Dejamos chocolate casi en cero
        self.insumo_chocolate.stock_actual = Decimal("0.200")
        self.insumo_chocolate.save()

        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            receta=self.receta_torta,
            cantidad=1, # Requiere 0.500 kg chocolate pero hay 0.200
            precio_unitario=self.receta_torta.precio_base,
        )
        pedido.recalcular_totales()
        pedido.save()
        emitir_cotizacion(pedido.id, self.vendedor)

        with self.assertRaises(ValidationError):
            confirmar_pedido(pedido.id, self.vendedor)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.COTIZADO)
        self.assertFalse(pedido.inventario_descontado)
        self.assertEqual(MovimientoInventario.objects.filter(pedido=pedido).count(), 0)

    def test_03_confirmar_cotizacion_vencida_falla(self):
        """Prueba 3: Falla si la cotización más reciente está vencida."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            receta=self.receta_torta,
            cantidad=1,
            precio_unitario=self.receta_torta.precio_base,
        )
        pedido.recalcular_totales()
        pedido.save()

        cot = emitir_cotizacion(pedido.id, self.vendedor)
        # Forzar vencimiento de la cotización
        cot.valida_hasta = timezone.localdate() - timedelta(days=1)
        cot.save()

        with self.assertRaises(ValidationError):
            confirmar_pedido(pedido.id, self.vendedor)

    def test_04_no_se_puede_confirmar_dos_veces(self):
        """Prueba 4: Idempotencia del descuento de stock por inventario_descontado."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            receta=self.receta_torta,
            cantidad=1,
            precio_unitario=self.receta_torta.precio_base,
        )
        pedido.recalcular_totales()
        pedido.save()
        emitir_cotizacion(pedido.id, self.vendedor)
        confirmar_pedido(pedido.id, self.vendedor)
        pedido.refresh_from_db()

        # Segundo intento directo al stock no vuelve a descontar
        movs = descontar_stock_pedido(pedido, self.vendedor)
        self.assertEqual(movs, [])

    def test_05_cancelar_pedido_reintegra_stock(self):
        """Prueba 5: Cancelar pedido revierte exactamente el stock con movimientos ENTRADA."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            receta=self.receta_torta,
            cantidad=1,
            precio_unitario=self.receta_torta.precio_base,
        )
        pedido.recalcular_totales()
        pedido.save()
        emitir_cotizacion(pedido.id, self.vendedor)
        confirmar_pedido(pedido.id, self.vendedor)

        # Cancelar pedido
        cancelar_pedido(pedido.id, self.vendedor, motivo="Cliente desiste")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.CANCELADO)
        self.assertFalse(pedido.inventario_descontado)

        # Stock vuelve exactamente a sus valores iniciales
        self.insumo_harina.refresh_from_db()
        self.assertEqual(self.insumo_harina.stock_actual, Decimal("10.000"))

        movs_entrada = MovimientoInventario.objects.filter(pedido=pedido, tipo=MovimientoInventario.Tipo.ENTRADA)
        self.assertEqual(movs_entrada.count(), 2)

    def test_06_transicion_kanban_invalida_devuelve_400(self):
        """Prueba 6: Saltar estados devuelve ValidationError / 400."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.CONFIRMADO, # Estado en Recibido
            fecha_entrega=timezone.now() + timedelta(days=1),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )

        # Intentar saltar directo a LISTO sin pasar por preparación
        with self.assertRaises(ValidationError):
            transicionar_estado(
                pedido_id=pedido.id,
                nuevo_estado=Pedido.Estado.LISTO,
                usuario=self.cocina,
                version=pedido.version,
            )

    def test_07_transicion_kanban_sin_version_correcta_devuelve_409(self):
        """Prueba 7: Conflicto optimista por versión desactualizada."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.CONFIRMADO,
            version=5,
            fecha_entrega=timezone.now() + timedelta(days=1),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )

        # Enviamos version 4 en vez de 5
        with self.assertRaises(ConflictError):
            transicionar_estado(
                pedido_id=pedido.id,
                nuevo_estado=Pedido.Estado.EN_PREPARACION,
                usuario=self.cocina,
                version=4,
            )

    def test_08_cocina_no_puede_confirmar_pedido(self):
        """Prueba 8: Cocina no tiene permisos de vendedor/admin para confirmar pedido (403)."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.COTIZADO,
            fecha_entrega=timezone.now() + timedelta(days=1),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        DetallePedido.objects.create(
            pedido=pedido, receta=self.receta_torta, cantidad=1, precio_unitario=Decimal("25000")
        )
        Cotizacion.objects.create(
            pedido=pedido,
            numero="COT-TEST-0001",
            valida_hasta=timezone.localdate() + timedelta(days=5),
            subtotal=Decimal("25000"),
            descuento=Decimal("0"),
            total=Decimal("25000"),
            estado=Cotizacion.Estado.VIGENTE,
        )

        with self.assertRaises(PermissionDenied):
            confirmar_pedido(pedido.id, self.cocina)

    def test_09_cliente_solo_ve_sus_pedidos(self):
        """Prueba 9: Aislamiento por rol: el cliente solo puede listar sus propios pedidos."""
        # Pedido del cliente
        p_propio = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Propio",
        )
        # Pedido de otro cliente
        p_ajeno = Pedido.objects.create(
            cliente=self.otro_cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Ajeno",
        )

        self.api_client.force_authenticate(user=self.usuario_cliente)
        res = self.api_client.get("/api/pedidos/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ids = [p["id"] for p in res.data["results"]] if "results" in res.data else [p["id"] for p in res.data]
        self.assertIn(p_propio.id, ids)
        self.assertNotIn(p_ajeno.id, ids)

    def test_10_despacho_requiere_firma_o_foto(self):
        """Prueba 10: Confirmar entrega sin firma ni foto lanza error de validación."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.LISTO,
            fecha_entrega=timezone.now(),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        ruta = RutaDespacho.objects.create(
            fecha=timezone.localdate(), repartidor=self.repartidor, estado=RutaDespacho.Estado.EN_RUTA
        )
        despacho = Despacho.objects.create(ruta=ruta, pedido=pedido, orden=1)

        with self.assertRaises(ValidationError):
            confirmar_entrega(
                despacho_id=despacho.id,
                receptor_nombre="Juan Pérez",
                firma_digital="",
                foto_comprobante=None,
            )

    def test_11_confirmar_entrega_cambia_estado_y_guarda_evidencia(self):
        """Prueba 11: Confirmar entrega con firma pasa pedido a ENTREGADO y guarda evidencia."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.LISTO,
            fecha_entrega=timezone.now(),
            direccion_entrega="Test",
            diseno_descripcion="Test",
        )
        ruta = RutaDespacho.objects.create(
            fecha=timezone.localdate(), repartidor=self.repartidor, estado=RutaDespacho.Estado.PLANIFICADA
        )
        despacho = Despacho.objects.create(ruta=ruta, pedido=pedido, orden=1)

        iniciar_ruta(ruta.id, self.repartidor)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.EN_DESPACHO)

        firma_valida = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        confirmar_entrega(
            despacho_id=despacho.id,
            receptor_nombre="Camila Silva",
            firma_digital=firma_valida,
            usuario=self.repartidor,
        )

        despacho.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(despacho.estado, Despacho.Estado.ENTREGADO)
        self.assertEqual(pedido.estado, Pedido.Estado.ENTREGADO)
        self.assertIsNotNone(pedido.fecha_entrega_real)

    def test_12_calculo_total_descuento_anticipo_saldo(self):
        """Prueba 12: Recálculo exacto con subtotal, descuento, anticipo y saldo."""
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=2),
            direccion_entrega="Test",
            diseno_descripcion="Test",
            descuento=Decimal("5000.00"),
        )
        DetallePedido.objects.create(
            pedido=pedido, receta=self.receta_torta, cantidad=2, precio_unitario=Decimal("25000.00")
        )
        pedido.recalcular_totales()
        pedido.save()

        # Subtotal: 50.000; Total: 50.000 - 5.000 = 45.000
        self.assertEqual(pedido.subtotal, Decimal("50000.00"))
        self.assertEqual(pedido.total, Decimal("45000.00"))
        self.assertEqual(pedido.saldo, Decimal("45000.00"))

        # Registrar pago de anticipo de 20.000
        Pago.objects.create(
            pedido=pedido,
            monto=Decimal("20000.00"),
            tipo=Pago.Tipo.ANTICIPO,
            metodo=Pago.Metodo.TRANSFERENCIA,
        )
        pedido.recalcular_totales()
        pedido.save()

        self.assertEqual(pedido.anticipo, Decimal("20000.00"))
        self.assertEqual(pedido.saldo, Decimal("25000.00"))

    def test_13_codigo_pedido_unico(self):
        """Prueba 13: El código de pedido se genera con formato DA-AAAA-NNNN y es único."""
        p1 = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=1),
            direccion_entrega="Test",
            diseno_descripcion="Test 1",
        )
        p1.generar_codigo()

        p2 = Pedido.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            estado=Pedido.Estado.BORRADOR,
            fecha_entrega=timezone.now() + timedelta(days=1),
            direccion_entrega="Test",
            diseno_descripcion="Test 2",
        )
        p2.generar_codigo()

        anio = timezone.now().year
        self.assertTrue(p1.codigo.startswith(f"DA-{anio}-"))
        self.assertTrue(p2.codigo.startswith(f"DA-{anio}-"))
        self.assertNotEqual(p1.codigo, p2.codigo)

    def test_14_stock_bajo_aparece_en_alertas(self):
        """Prueba 14: Insumo con stock_actual <= stock_minimo reporta stock_bajo=True."""
        insumo_bajo = Insumo.objects.create(
            nombre="Almendra Molida",
            categoria=Insumo.Categoria.OTROS,
            unidad=Insumo.Unidad.KG,
            stock_actual=Decimal("1.500"),
            stock_minimo=Decimal("5.000"),
            costo_unitario=Decimal("8000"),
        )
        self.assertTrue(insumo_bajo.stock_bajo)

        self.api_client.force_authenticate(user=self.admin)
        res = self.api_client.get("/api/insumos/alertas/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        nombres = [item["nombre"] for item in res.data["bajo_stock"]]
        self.assertIn("Almendra Molida", nombres)

    def test_15_receta_costo_y_margen(self):
        """Prueba 15: Cálculo fiel de costo_insumos, costo unitario y margen real."""
        # 1 kg harina (5% merma = 1.05 kg * $1000 = $1050)
        # 0.5 kg chocolate (0% merma = 0.5 kg * $10000 = $5000)
        # Costo total insumos = $6050
        costo_esperado = Decimal("6050.00")
        self.assertEqual(self.receta_torta.costo_insumos, costo_esperado)
        self.assertEqual(self.receta_torta.costo_unitario_produccion, costo_esperado)

        # Precio base: $25000. Margen = (25000 - 6050) / 25000 = 75.8%
        margen = self.receta_torta.margen_real
        self.assertAlmostEqual(float(margen), 75.8, places=1)

    def test_16_smoke_vistas_principales(self):
        """Prueba 16: Prueba de humo de vistas principales con autenticación."""
        self.client.login(username="admin_test", password="Password123!")
        rutas_a_probar = [
            reverse("dashboard:index"),
            reverse("pedidos:index"),
            reverse("pedidos:nuevo"),
            reverse("pedidos:kanban"),
            reverse("catalogo:index"),
            reverse("catalogo:insumos"),
            reverse("despachos:index"),
            reverse("dashboard:reportes"),
        ]
        for url in rutas_a_probar:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Falla en vista {url}")
