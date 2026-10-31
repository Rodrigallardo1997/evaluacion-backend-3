"""
Comando de gestión para sembrar datos demo iniciales e idempotentes en Dulce Arte.
Crea usuarios por rol, clientes, insumos con stock/alertas, recetas con BOM,
pedidos en todos los estados del flujo Kanban y rutas de despacho.
"""
from datetime import timedelta
from decimal import Decimal
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Insumo, Receta, RecetaInsumo
from apps.despachos.models import RutaDespacho, Despacho
from apps.inventario.models import MovimientoInventario
from apps.pedidos.models import (
    Cliente,
    Pedido,
    DetallePedido,
    Cotizacion,
    HistorialEstadoPedido,
    Pago,
)
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = "Siembra datos iniciales completos y realistas para la demostración de Dulce Arte."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando sembrado de datos demo para Dulce Arte..."))

        with transaction.atomic():
            usuarios = self._crear_usuarios()
            clientes = self._crear_clientes(usuarios["cliente"])
            insumos = self._crear_insumos()
            recetas = self._crear_recetas(insumos)
            pedidos = self._crear_pedidos(clientes, usuarios, recetas, insumos)
            self._crear_rutas(usuarios["repartidor"], usuarios["admin"], pedidos)

        self.stdout.write(self.style.SUCCESS("[OK] Datos demo creados exitosamente de forma idempotente."))
        self._imprimir_resumen()

    def _crear_usuarios(self):
        usuarios_data = [
            ("admin", "Admin123!", Usuario.Rol.ADMIN, "Rodrigo", "Gallardo", True, True, "+56 9 8888 1111"),
            ("vendedor", "Vendedor123!", Usuario.Rol.VENDEDOR, "Valentina", "Pérez", True, False, "+56 9 7777 2222"),
            ("cocina", "Cocina123!", Usuario.Rol.COCINA, "Chef Claudio", "Muñoz", True, False, "+56 9 6666 3333"),
            ("repartidor", "Reparto123!", Usuario.Rol.REPARTIDOR, "Carlos", "Soto", True, False, "+56 9 5555 4444"),
            ("cliente", "Cliente123!", Usuario.Rol.CLIENTE, "Camila", "Silva", False, False, "+56 9 4444 5555"),
        ]

        usuarios = {}
        for username, password, rol, first_name, last_name, is_staff, is_superuser, tel in usuarios_data:
            user, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@dulcearte.cl",
                    "first_name": first_name,
                    "last_name": last_name,
                    "rol": rol,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                    "telefono": tel,
                },
            )
            user.set_password(password)
            user.rol = rol
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.telefono = tel
            user.save()
            usuarios[username] = user

        return usuarios

    def _crear_clientes(self, usuario_cliente):
        clientes_data = [
            ("Camila Silva Edwards", "16.842.109-3", "+56 9 4444 5555", "camila.silva@gmail.com", "Av. Providencia 2045, Depto 402, Providencia", "Frente a Metro Los Leones", usuario_cliente),
            ("Ignacio Morales Castro", "15.421.908-K", "+56 9 8123 4567", "ignacio.morales@empresa.cl", "Av. Apoquindo 4800, Torre 2, Piso 10, Las Condes", "Recepción edificio corporativo", None),
            ("María José Vergara", "18.312.456-7", "+56 9 9234 5678", "mjose.vergara@yahoo.com", "Calle Huérfanos 1150, Depto 12B, Santiago Centro", "Timbre 12B portón café", None),
            ("Sebastián Valenzuela Rios", "17.654.321-1", "+56 9 7345 6789", "svalenzuela@gmail.com", "Av. Irarrázaval 3450, Casa 4, Ñuñoa", "Condominio Los Cerezos", None),
            ("Daniela Herrera Tapia", "19.876.543-2", "+56 9 6456 7890", "daniela.herrera@outlook.com", "Av. Vicuña Mackenna 7100, La Florida", "Cerca de Metro Bellavista de La Florida", None),
            ("Gonzalo Larraín Bulnes", "14.567.890-4", "+56 9 5567 8901", "glarrain@inversiones.cl", "Av. Vitacura 5200, Vitacura", "Casa fachada blanca con guardia", None),
        ]

        clientes = []
        for nombre, rut, tel, email, direccion, ref, user in clientes_data:
            cliente, _ = Cliente.objects.update_or_create(
                rut=rut,
                defaults={
                    "nombre_completo": nombre,
                    "telefono": tel,
                    "email": email,
                    "direccion": direccion,
                    "referencia_direccion": ref,
                    "usuario": user,
                    "activo": True,
                },
            )
            clientes.append(cliente)
        return clientes

    def _crear_insumos(self):
        hoy = timezone.localdate()
        insumos_data = [
            ("Harina de Trigo Especial", Insumo.Categoria.HARINAS, Insumo.Unidad.KG, Decimal("60.000"), Decimal("20.000"), Decimal("1200"), False, None),
            ("Azúcar Flor Fina", Insumo.Categoria.AZUCARES, Insumo.Unidad.KG, Decimal("8.500"), Decimal("15.000"), Decimal("1450"), False, None), # Stock bajo
            ("Mantequilla con Sal Extra", Insumo.Categoria.LACTEOS, Insumo.Unidad.KG, Decimal("18.000"), Decimal("8.000"), Decimal("4800"), True, hoy + timedelta(days=25)),
            ("Chocolate Belga 70% Cacao", Insumo.Categoria.CHOCOLATES, Insumo.Unidad.KG, Decimal("4.000"), Decimal("10.000"), Decimal("12500"), False, None), # Stock bajo
            ("Crema de Leche Pastelera 35%", Insumo.Categoria.LACTEOS, Insumo.Unidad.L, Decimal("25.000"), Decimal("10.000"), Decimal("2950"), True, hoy + timedelta(days=14)),
            ("Huevos de Campo Seleccionados", Insumo.Categoria.HUEVOS, Insumo.Unidad.UNIDAD, Decimal("180.000"), Decimal("40.000"), Decimal("220"), True, hoy + timedelta(days=18)),
            ("Extracto Vainilla Bourbon", Insumo.Categoria.OTROS, Insumo.Unidad.ML, Decimal("650.000"), Decimal("150.000"), Decimal("18"), False, None),
            ("Frutillas Frescas del Maule", Insumo.Categoria.FRUTAS, Insumo.Unidad.KG, Decimal("3.000"), Decimal("6.000"), Decimal("3400"), True, hoy - timedelta(days=2)), # Vencido
            ("Granos de Café Arábica de Especialidad", Insumo.Categoria.OTROS, Insumo.Unidad.KG, Decimal("15.000"), Decimal("5.000"), Decimal("16000"), False, None),
            ("Harina de Almendras Finas", Insumo.Categoria.HARINAS, Insumo.Unidad.KG, Decimal("10.000"), Decimal("3.000"), Decimal("11500"), False, None),
            ("Nueces Chilenas Peladas", Insumo.Categoria.OTROS, Insumo.Unidad.KG, Decimal("8.000"), Decimal("3.000"), Decimal("8900"), False, None),
            ("Canela de Ceilán en Polvo", Insumo.Categoria.OTROS, Insumo.Unidad.KG, Decimal("5.000"), Decimal("1.500"), Decimal("14000"), False, None),
            ("Queso Crema Pastelero", Insumo.Categoria.LACTEOS, Insumo.Unidad.KG, Decimal("14.000"), Decimal("5.000"), Decimal("6200"), True, hoy + timedelta(days=20)),
            ("Limones Sutiles Frescos", Insumo.Categoria.FRUTAS, Insumo.Unidad.KG, Decimal("12.000"), Decimal("4.000"), Decimal("1800"), True, hoy + timedelta(days=10)),
            ("Leche Condensada Pastelera", Insumo.Categoria.LACTEOS, Insumo.Unidad.KG, Decimal("20.000"), Decimal("8.000"), Decimal("3200"), True, hoy + timedelta(days=60)),
            ("Manjar de Campo Tradicional", Insumo.Categoria.LACTEOS, Insumo.Unidad.KG, Decimal("16.000"), Decimal("6.000"), Decimal("3800"), True, hoy + timedelta(days=45)),
            ("Té Negro en Hebras Especiado", Insumo.Categoria.OTROS, Insumo.Unidad.KG, Decimal("6.000"), Decimal("2.000"), Decimal("18500"), False, None),
        ]

        insumos = {}
        for nombre, cat, uni, stock, min_s, costo, perecible, vencimiento in insumos_data:
            insumo, _ = Insumo.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "categoria": cat,
                    "unidad": uni,
                    "stock_actual": stock,
                    "stock_minimo": min_s,
                    "costo_unitario": costo,
                    "perecedero": perecible,
                    "fecha_vencimiento": vencimiento,
                    "activo": True,
                },
            )
            insumos[nombre] = insumo
        return insumos

    def _crear_recetas(self, insumos):
        recetas_data = [
            (
                "Torta Chocolate Belga Suprema",
                Receta.Categoria.TORTA,
                "Bizcochuelo húmedo de cacao con doble relleno de trufa belga al 70% y baño espejado.",
                1,
                Decimal("32000"),
                Decimal("35"),
                90,
                [
                    ("Harina de Trigo Especial", Decimal("0.400"), Decimal("2.0")),
                    ("Chocolate Belga 70% Cacao", Decimal("0.350"), Decimal("1.5")),
                    ("Mantequilla con Sal Extra", Decimal("0.250"), Decimal("3.0")),
                    ("Azúcar Flor Fina", Decimal("0.300"), Decimal("1.0")),
                    ("Huevos de Campo Seleccionados", Decimal("6.000"), Decimal("0.0")),
                ],
            ),
            (
                "Cheesecake Clásico New York",
                Receta.Categoria.POSTRE,
                "Tradicional cheesecake horneado a baja temperatura con base de galletas y reducción cítrica.",
                1,
                Decimal("28000"),
                Decimal("30"),
                120,
                [
                    ("Crema de Leche Pastelera 35%", Decimal("0.600"), Decimal("2.0")),
                    ("Queso Crema Pastelero", Decimal("0.500"), Decimal("1.5")),
                    ("Mantequilla con Sal Extra", Decimal("0.200"), Decimal("2.0")),
                    ("Azúcar Flor Fina", Decimal("0.250"), Decimal("1.0")),
                    ("Huevos de Campo Seleccionados", Decimal("4.000"), Decimal("0.0")),
                    ("Extracto Vainilla Bourbon", Decimal("15.000"), Decimal("0.0")),
                ],
            ),
            (
                "Caja 12 Galletas Glaseadas Gourmet",
                Receta.Categoria.GALLETA,
                "Galletas de mantequilla y vainilla fina decoradas artesanalmente con glaseado real temático.",
                12,
                Decimal("16500"),
                Decimal("40"),
                60,
                [
                    ("Harina de Trigo Especial", Decimal("0.500"), Decimal("2.0")),
                    ("Mantequilla con Sal Extra", Decimal("0.250"), Decimal("2.0")),
                    ("Azúcar Flor Fina", Decimal("0.200"), Decimal("1.0")),
                    ("Huevos de Campo Seleccionados", Decimal("2.000"), Decimal("0.0")),
                ],
            ),
            (
                "Torta Frutos Rojos y Crema Chantilly",
                Receta.Categoria.TORTA,
                "Bizcocho genovés de vainilla relleno con crema pastelera batida y compota fresca de frutos rojos.",
                1,
                Decimal("29500"),
                Decimal("32"),
                75,
                [
                    ("Harina de Trigo Especial", Decimal("0.350"), Decimal("2.0")),
                    ("Crema de Leche Pastelera 35%", Decimal("0.500"), Decimal("3.0")),
                    ("Azúcar Flor Fina", Decimal("0.250"), Decimal("1.0")),
                    ("Huevos de Campo Seleccionados", Decimal("5.000"), Decimal("0.0")),
                    ("Extracto Vainilla Bourbon", Decimal("10.000"), Decimal("0.0")),
                ],
            ),
            (
                "Pie de Limón Merengado Artesanal",
                Receta.Categoria.POSTRE,
                "Masa quebrada crocante rellena de suave crema de limón sutil y coronada con merengue italiano flameado.",
                1,
                Decimal("22000"),
                Decimal("35"),
                70,
                [
                    ("Harina de Trigo Especial", Decimal("0.350"), Decimal("2.0")),
                    ("Mantequilla con Sal Extra", Decimal("0.180"), Decimal("1.0")),
                    ("Limones Sutiles Frescos", Decimal("0.400"), Decimal("5.0")),
                    ("Leche Condensada Pastelera", Decimal("0.400"), Decimal("1.0")),
                    ("Huevos de Campo Seleccionados", Decimal("4.000"), Decimal("0.0")),
                    ("Azúcar Flor Fina", Decimal("0.200"), Decimal("1.0")),
                ],
            ),
            (
                "Torta Tres Leches Tradicional con Canela",
                Receta.Categoria.TORTA,
                "Esponjoso bizcochuelo bañado en mezcla de tres leches, manjar de campo artesanal y merengue con canela.",
                1,
                Decimal("26500"),
                Decimal("33"),
                80,
                [
                    ("Harina de Trigo Especial", Decimal("0.300"), Decimal("2.0")),
                    ("Huevos de Campo Seleccionados", Decimal("5.000"), Decimal("0.0")),
                    ("Azúcar Flor Fina", Decimal("0.200"), Decimal("1.0")),
                    ("Crema de Leche Pastelera 35%", Decimal("0.350"), Decimal("2.0")),
                    ("Leche Condensada Pastelera", Decimal("0.350"), Decimal("1.0")),
                    ("Manjar de Campo Tradicional", Decimal("0.250"), Decimal("1.0")),
                    ("Canela de Ceilán en Polvo", Decimal("0.015"), Decimal("0.0")),
                ],
            ),
            (
                "Box 6 Macarons Franceses Surtidos",
                Receta.Categoria.DULCE,
                "Macarons artesanales con cascarón crocante y corazón suave de pistacho, frambuesa y ganache belga.",
                6,
                Decimal("12500"),
                Decimal("45"),
                60,
                [
                    ("Harina de Almendras Finas", Decimal("0.160"), Decimal("2.0")),
                    ("Azúcar Flor Fina", Decimal("0.200"), Decimal("1.0")),
                    ("Huevos de Campo Seleccionados", Decimal("3.000"), Decimal("0.0")),
                    ("Chocolate Belga 70% Cacao", Decimal("0.080"), Decimal("1.0")),
                    ("Crema de Leche Pastelera 35%", Decimal("0.080"), Decimal("2.0")),
                ],
            ),
            (
                "Brownie Fudge con Nueces Seleccionadas",
                Receta.Categoria.DULCE,
                "Cuadrados húmedos e intensos de chocolate amargo 70% con trozos de nueces crocantes y toque de vainilla.",
                4,
                Decimal("8500"),
                Decimal("40"),
                45,
                [
                    ("Chocolate Belga 70% Cacao", Decimal("0.200"), Decimal("1.5")),
                    ("Mantequilla con Sal Extra", Decimal("0.140"), Decimal("2.0")),
                    ("Harina de Trigo Especial", Decimal("0.120"), Decimal("2.0")),
                    ("Huevos de Campo Seleccionados", Decimal("3.000"), Decimal("0.0")),
                    ("Azúcar Flor Fina", Decimal("0.180"), Decimal("1.0")),
                    ("Nueces Chilenas Peladas", Decimal("0.100"), Decimal("3.0")),
                ],
            ),
            (
                "Pack 4 Rollos de Canela Glaseados",
                Receta.Categoria.DULCE,
                "Masa brioche horneada lentamente, perfumada con canela de Ceilán y cubierta con glaseado de queso crema.",
                4,
                Decimal("9900"),
                Decimal("38"),
                75,
                [
                    ("Harina de Trigo Especial", Decimal("0.400"), Decimal("2.0")),
                    ("Mantequilla con Sal Extra", Decimal("0.120"), Decimal("2.0")),
                    ("Huevos de Campo Seleccionados", Decimal("2.000"), Decimal("0.0")),
                    ("Azúcar Flor Fina", Decimal("0.150"), Decimal("1.0")),
                    ("Canela de Ceilán en Polvo", Decimal("0.035"), Decimal("1.0")),
                    ("Queso Crema Pastelero", Decimal("0.120"), Decimal("2.0")),
                ],
            ),
            (
                "Café Espresso Doble de Especialidad",
                Receta.Categoria.CAFETERIA,
                "Extracción doble de granos 100% arábica tostado medio con cuerpo sedoso, acidez brillante y notas a avellana.",
                1,
                Decimal("2800"),
                Decimal("60"),
                5,
                [
                    ("Granos de Café Arábica de Especialidad", Decimal("0.020"), Decimal("5.0")),
                ],
            ),
            (
                "Cappuccino Vainilla Francesa",
                Receta.Categoria.CAFETERIA,
                "Espresso doble con leche cremosa vaporizada, microespuma brillante y sutil jarabe natural de vainilla bourbon.",
                1,
                Decimal("3800"),
                Decimal("55"),
                8,
                [
                    ("Granos de Café Arábica de Especialidad", Decimal("0.020"), Decimal("5.0")),
                    ("Crema de Leche Pastelera 35%", Decimal("0.160"), Decimal("3.0")),
                    ("Extracto Vainilla Bourbon", Decimal("8.000"), Decimal("0.0")),
                ],
            ),
            (
                "Chocolate Caliente Artesanal Suizo",
                Receta.Categoria.CAFETERIA,
                "Leche entera texturizada fundida con auténtico chocolate belga 70% cacao y toque de canela aromática.",
                1,
                Decimal("4200"),
                Decimal("50"),
                10,
                [
                    ("Chocolate Belga 70% Cacao", Decimal("0.080"), Decimal("2.0")),
                    ("Crema de Leche Pastelera 35%", Decimal("0.220"), Decimal("3.0")),
                    ("Azúcar Flor Fina", Decimal("0.025"), Decimal("1.0")),
                    ("Canela de Ceilán en Polvo", Decimal("0.003"), Decimal("0.0")),
                ],
            ),
            (
                "Chai Latte Especiado en Leche Texturizada",
                Receta.Categoria.CAFETERIA,
                "Infusión aromática de té negro con canela, clavo de olor y cardamomo, combinada con suave leche cremosa.",
                1,
                Decimal("3900"),
                Decimal("55"),
                8,
                [
                    ("Té Negro en Hebras Especiado", Decimal("0.015"), Decimal("2.0")),
                    ("Crema de Leche Pastelera 35%", Decimal("0.200"), Decimal("3.0")),
                    ("Canela de Ceilán en Polvo", Decimal("0.005"), Decimal("0.0")),
                    ("Azúcar Flor Fina", Decimal("0.020"), Decimal("1.0")),
                ],
            ),
        ]

        recetas = {}
        mapa_imagenes = {
            "Torta Chocolate Belga Suprema": "recetas/torta_chocolate.jpg",
            "Cheesecake Clásico New York": "recetas/cheesecake.jpg",
            "Caja 12 Galletas Glaseadas Gourmet": "recetas/galletas.jpg",
            "Torta Frutos Rojos y Crema Chantilly": "recetas/torta_frutos_rojos.jpg",
            "Pie de Limón Merengado Artesanal": "recetas/pie_limon.jpg",
            "Torta Tres Leches Tradicional con Canela": "recetas/tres_leches.jpg",
            "Box 6 Macarons Franceses Surtidos": "recetas/macarons.jpg",
            "Brownie Fudge con Nueces Seleccionadas": "recetas/brownie.jpg",
            "Pack 4 Rollos de Canela Glaseados": "recetas/cinnamon_rolls.jpg",
            "Café Espresso Doble de Especialidad": "recetas/espresso.jpg",
            "Cappuccino Vainilla Francesa": "recetas/cappuccino.jpg",
            "Chocolate Caliente Artesanal Suizo": "recetas/chocolate_caliente.jpg",
            "Chai Latte Especiado en Leche Texturizada": "recetas/chai_latte.jpg",
        }
        for nombre, cat, desc, rend, precio, margen, tiempo, bom in recetas_data:
            receta, _ = Receta.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "categoria": cat,
                    "descripcion": desc,
                    "rendimiento": rend,
                    "precio_base": precio,
                    "margen_deseado": margen,
                    "tiempo_preparacion_min": tiempo,
                    "imagen": mapa_imagenes.get(nombre, ""),
                    "activo": True,
                },
            )
            # Recrear BOM
            receta.insumos.all().delete()
            for ins_nombre, cant, merma in bom:
                RecetaInsumo.objects.create(
                    receta=receta,
                    insumo=insumos[ins_nombre],
                    cantidad=cant,
                    merma_porcentaje=merma,
                )
            recetas[nombre] = receta
        return recetas

    def _crear_pedidos(self, clientes, usuarios, recetas, insumos):
        hoy = timezone.now()
        vendedor = usuarios["vendedor"]
        cocina = usuarios["cocina"]

        pedidos_def = [
            # 1. BORRADOR
            {
                "codigo": f"DA-{hoy.year}-0001",
                "cliente": clientes[0],
                "estado": Pedido.Estado.BORRADOR,
                "prioridad": Pedido.Prioridad.MEDIA,
                "fecha_entrega": hoy + timedelta(days=4, hours=2),
                "direccion": clientes[0].direccion,
                "diseno": "Pastel de cumpleaños 30 años, tonos pastel rosa y blanco, dedicatoria 'Feliz Cumple Cami'.",
                "receta": recetas["Torta Chocolate Belga Suprema"],
                "cantidad": 1,
                "descuento": Decimal("0"),
            },
            # 2. COTIZADO
            {
                "codigo": f"DA-{hoy.year}-0002",
                "cliente": clientes[1],
                "estado": Pedido.Estado.COTIZADO,
                "prioridad": Pedido.Prioridad.ALTA,
                "fecha_entrega": hoy + timedelta(days=3, hours=5),
                "direccion": clientes[1].direccion,
                "diseno": "Logo corporativo de empresa en oblea de azúcar sobre cheesecake para aniversario 10 años.",
                "receta": recetas["Cheesecake Clásico New York"],
                "cantidad": 2,
                "descuento": Decimal("3000"),
            },
            # 3. CONFIRMADO (Recibido en Kanban)
            {
                "codigo": f"DA-{hoy.year}-0003",
                "cliente": clientes[2],
                "estado": Pedido.Estado.CONFIRMADO,
                "prioridad": Pedido.Prioridad.MEDIA,
                "fecha_entrega": hoy + timedelta(days=2, hours=3),
                "direccion": clientes[2].direccion,
                "diseno": "Temática bosque encantado con pequeñas flores de azúcar y frutos rojos.",
                "receta": recetas["Torta Frutos Rojos y Crema Chantilly"],
                "cantidad": 1,
                "descuento": Decimal("0"),
                "anticipo": Decimal("15000"),
            },
            # 4. EN_PREPARACION (Cocina)
            {
                "codigo": f"DA-{hoy.year}-0004",
                "cliente": clientes[3],
                "estado": Pedido.Estado.EN_PREPARACION,
                "prioridad": Pedido.Prioridad.URGENTE,
                "fecha_entrega": hoy + timedelta(hours=6),
                "direccion": clientes[3].direccion,
                "diseno": "Bautizo niño con angelito modelado y cinta celeste pastel.",
                "receta": recetas["Torta Chocolate Belga Suprema"],
                "cantidad": 1,
                "descuento": Decimal("0"),
                "anticipo": Decimal("20000"),
            },
            # 5. HORNEADO_DECORADO (Cocina)
            {
                "codigo": f"DA-{hoy.year}-0005",
                "cliente": clientes[4],
                "estado": Pedido.Estado.HORNEADO_DECORADO,
                "prioridad": Pedido.Prioridad.ALTA,
                "fecha_entrega": hoy + timedelta(hours=8),
                "direccion": clientes[4].direccion,
                "diseno": "Decoración temática dinosaurios infantiles para 15 niños.",
                "receta": recetas["Caja 12 Galletas Glaseadas Gourmet"],
                "cantidad": 2,
                "descuento": Decimal("1000"),
                "anticipo": Decimal("16000"),
            },
            # 6. CONTROL_CALIDAD (Cocina)
            {
                "codigo": f"DA-{hoy.year}-0006",
                "cliente": clientes[5],
                "estado": Pedido.Estado.CONTROL_CALIDAD,
                "prioridad": Pedido.Prioridad.MEDIA,
                "fecha_entrega": hoy + timedelta(hours=10),
                "direccion": clientes[5].direccion,
                "diseno": "Elegante estilo naked cake con toques dorados y flores naturales comestibles.",
                "receta": recetas["Cheesecake Clásico New York"],
                "cantidad": 1,
                "descuento": Decimal("0"),
                "anticipo": Decimal("28000"),
            },
            # 7. LISTO (Listo para Despacho)
            {
                "codigo": f"DA-{hoy.year}-0007",
                "cliente": clientes[0],
                "estado": Pedido.Estado.LISTO,
                "prioridad": Pedido.Prioridad.URGENTE,
                "fecha_entrega": hoy + timedelta(hours=3),
                "direccion": clientes[0].direccion,
                "diseno": "Caja de galletas surtidas con moño artesanal rosado.",
                "receta": recetas["Caja 12 Galletas Glaseadas Gourmet"],
                "cantidad": 1,
                "descuento": Decimal("0"),
                "anticipo": Decimal("16500"),
            },
            # 8. ENTREGADO (Con evidencia)
            {
                "codigo": f"DA-{hoy.year}-0008",
                "cliente": clientes[1],
                "estado": Pedido.Estado.ENTREGADO,
                "prioridad": Pedido.Prioridad.MEDIA,
                "fecha_entrega": hoy - timedelta(hours=2),
                "direccion": clientes[1].direccion,
                "diseno": "Torta frutos rojos con dedicatoria de aniversario.",
                "receta": recetas["Torta Frutos Rojos y Crema Chantilly"],
                "cantidad": 1,
                "descuento": Decimal("0"),
                "anticipo": Decimal("29500"),
            },
        ]

        pedidos_creados = []
        for p_data in pedidos_def:
            pedido, _ = Pedido.objects.update_or_create(
                codigo=p_data["codigo"],
                defaults={
                    "cliente": p_data["cliente"],
                    "vendedor": vendedor,
                    "estado": p_data["estado"],
                    "prioridad": p_data["prioridad"],
                    "fecha_entrega": p_data["fecha_entrega"],
                    "direccion_entrega": p_data["direccion"],
                    "diseno_descripcion": p_data["diseno"],
                    "descuento": p_data["descuento"],
                    "inventario_descontado": p_data["estado"] not in [Pedido.Estado.BORRADOR, Pedido.Estado.COTIZADO],
                    "fecha_entrega_real": hoy if p_data["estado"] == Pedido.Estado.ENTREGADO else None,
                },
            )

            # Detalle
            DetallePedido.objects.filter(pedido=pedido).delete()
            DetallePedido.objects.create(
                pedido=pedido,
                receta=p_data["receta"],
                cantidad=p_data["cantidad"],
                precio_unitario=p_data["receta"].precio_base,
            )

            # Pagos
            Pago.objects.filter(pedido=pedido).delete()
            if "anticipo" in p_data and p_data["anticipo"] > 0:
                Pago.objects.create(
                    pedido=pedido,
                    monto=p_data["anticipo"],
                    tipo=Pago.Tipo.ANTICIPO,
                    metodo=Pago.Metodo.TRANSFERENCIA,
                    referencia="TRANSF-BANCO-CHILE-9988",
                    registrado_por=vendedor,
                )

            pedido.recalcular_totales()
            pedido.save()

            # Cotización si corresponde
            if p_data["estado"] != Pedido.Estado.BORRADOR:
                Cotizacion.objects.filter(pedido=pedido).delete()
                Cotizacion.objects.create(
                    pedido=pedido,
                    numero=f"COT-{hoy.year}-{pedido.pk:04d}",
                    valida_hasta=timezone.localdate() + timedelta(days=7),
                    subtotal=pedido.subtotal,
                    descuento=pedido.descuento,
                    total=pedido.total,
                    estado=Cotizacion.Estado.ACEPTADA if p_data["estado"] != Pedido.Estado.COTIZADO else Cotizacion.Estado.VIGENTE,
                    creado_por=vendedor,
                    condiciones="Cotización formal demo de pastelería artesanal.",
                )

            # Historial
            HistorialEstadoPedido.objects.filter(pedido=pedido).delete()
            HistorialEstadoPedido.objects.create(
                pedido=pedido,
                estado_anterior=Pedido.Estado.BORRADOR,
                estado_nuevo=pedido.estado,
                usuario=vendedor,
                observacion=f"Pedido generado en estado {pedido.get_estado_display()} para demostración.",
            )

            # Movimiento inventario si fue descontado
            if pedido.inventario_descontado:
                MovimientoInventario.objects.filter(pedido=pedido).delete()
                insumo_ref = insumos["Harina de Trigo Especial"]
                MovimientoInventario.objects.create(
                    insumo=insumo_ref,
                    tipo=MovimientoInventario.Tipo.SALIDA,
                    cantidad=Decimal("0.400"),
                    stock_anterior=insumo_ref.stock_actual + Decimal("0.400"),
                    stock_nuevo=insumo_ref.stock_actual,
                    motivo=f"Consumo pedido {pedido.codigo}",
                    pedido=pedido,
                    usuario=vendedor,
                )

            pedidos_creados.append(pedido)

        return pedidos_creados

    def _crear_rutas(self, repartidor, admin_user, pedidos):
        hoy = timezone.localdate()

        # Ruta 1: Planificada
        ruta_planificada, _ = RutaDespacho.objects.update_or_create(
            codigo=f"RUTA-{hoy.year}-0001",
            defaults={
                "fecha": hoy,
                "repartidor": repartidor,
                "vehiculo": "Furgón Peugeot Partner ABCD-12",
                "estado": RutaDespacho.Estado.PLANIFICADA,
                "observaciones": "Ruta sector Oriente: Providencia, Las Condes y Vitacura.",
                "creado_por": admin_user,
            },
        )
        Despacho.objects.filter(ruta=ruta_planificada).delete()
        # Asignar pedido LISTO
        pedido_listo = next(p for p in pedidos if p.estado == Pedido.Estado.LISTO)
        Despacho.objects.create(
            ruta=ruta_planificada,
            pedido=pedido_listo,
            orden=1,
            estado=Despacho.Estado.PENDIENTE,
        )

        # Ruta 2: En ruta / entregada
        ruta_en_ruta, _ = RutaDespacho.objects.update_or_create(
            codigo=f"RUTA-{hoy.year}-0002",
            defaults={
                "fecha": hoy,
                "repartidor": repartidor,
                "vehiculo": "Moto Honda Cargo EFGH-34",
                "estado": RutaDespacho.Estado.COMPLETADA,
                "observaciones": "Ruta entregas express Santiago Centro.",
                "creado_por": admin_user,
            },
        )
        Despacho.objects.filter(ruta=ruta_en_ruta).delete()
        pedido_entregado = next(p for p in pedidos if p.estado == Pedido.Estado.ENTREGADO)
        # Firma digital demo en Data URL Base64
        firma_demo = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKAAAABaCAYAAABzD3+eAAAACXBIWXMAAAsTAAALEwEAmpwYAAAC"
            "tUlEQVR4nO3bQW6DMBBA0en9D50tyqKqVf8sxhh5L2FBEz0b2zEGAAAAAAAAAAAAAAAAAAAAAAAA4B/N83wppfQ65/l+3/da63"
            "meZ+99jTG21lprba31/dznOT6fzz+P5/P553Ge53kcx3G8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8z/M8"
            "w/eR6P12u/f3wHfgHj0j6R7sN3wAAAAABJRU5ErkJggg=="
        )
        Despacho.objects.create(
            ruta=ruta_en_ruta,
            pedido=pedido_entregado,
            orden=1,
            estado=Despacho.Estado.ENTREGADO,
            receptor_nombre=pedido_entregado.cliente.nombre_completo,
            firma_digital=firma_demo,
            fecha_entrega=timezone.now() - timedelta(hours=2),
            observaciones="Entrega confirmada con firma digital en pantalla.",
        )

    def _imprimir_resumen(self):
        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(self.style.SUCCESS("RESUMEN DE CREDENCIALES DEMO — DULCE ARTE"))
        self.stdout.write("=" * 65)
        self.stdout.write("Rol          | Usuario      | Contraseña   | Nombre")
        self.stdout.write("-" * 65)
        self.stdout.write("ADMIN        | admin        | Admin123!    | Rodrigo Gallardo")
        self.stdout.write("VENDEDOR     | vendedor     | Vendedor123! | Valentina Pérez")
        self.stdout.write("COCINA       | cocina       | Cocina123!   | Claudio Muñoz")
        self.stdout.write("REPARTIDOR   | repartidor   | Reparto123!  | Carlos Soto")
        self.stdout.write("CLIENTE      | cliente      | Cliente123!  | Camila Silva")
        self.stdout.write("=" * 65 + "\n")
