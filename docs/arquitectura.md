# Arquitectura del Sistema Dulce Arte (Vistas 4+1)

El sistema **Dulce Arte** implementa una arquitectura en capas desacoplada para garantizar trazabilidad end-to-end, concurrencia segura y alta mantenibilidad. Se documenta bajo el modelo **4+1 Vistas de Kruchten**.

---

## 1. Vista Lógica (Entidades y Relaciones del Dominio)

La vista lógica modela las entidades fundamentales del negocio y sus relaciones:

```mermaid
classDiagram
    class Usuario {
        +String username
        +Rol rol
        +String telefono
        +Boolean is_staff
    }

    class Cliente {
        +String nombre_completo
        +String rut
        +String telefono
        +String direccion
    }

    class Insumo {
        +String nombre
        +Categoria categoria
        +Decimal stock_actual
        +Decimal stock_minimo
        +Decimal costo_unitario
        +Boolean perecedero
        +Date fecha_vencimiento
    }

    class Receta {
        +String nombre
        +PositiveInt rendimiento
        +Decimal precio_base
        +Decimal margen_deseado
        +costo_insumos()
        +costo_unitario_produccion()
        +margen_real()
    }

    class RecetaInsumo {
        +Decimal cantidad
        +Decimal merma_porcentaje
        +cantidad_neta()
    }

    class Pedido {
        +String codigo
        +Estado estado
        +Prioridad prioridad
        +DateTime fecha_entrega
        +Decimal total
        +Decimal anticipo
        +Decimal saldo
        +Boolean inventario_descontado
        +PositiveInt version
    }

    class DetallePedido {
        +PositiveInt cantidad
        +Decimal precio_unitario
        +subtotal()
    }

    class Cotizacion {
        +String numero
        +Date valida_hasta
        +Decimal total
        +Estado estado
    }

    class MovimientoInventario {
        +Tipo tipo
        +Decimal cantidad
        +Decimal stock_anterior
        +Decimal stock_nuevo
        +String motivo
    }

    class RutaDespacho {
        +String codigo
        +Date fecha
        +Estado estado
    }

    class Despacho {
        +PositiveInt orden
        +Estado estado
        +String receptor_nombre
        +String firma_digital
        +Image foto_comprobante
    }

    Usuario "1" --> "0..1" Cliente : vinculado
    Cliente "1" --> "*" Pedido : solicita
    Usuario "1" --> "*" Pedido : vende
    Pedido "1" *-- "*" DetallePedido : contiene
    Receta "1" <-- "*" DetallePedido : referencia
    Receta "1" *-- "*" RecetaInsumo : BOM
    Insumo "1" <-- "*" RecetaInsumo : consume
    Pedido "1" *-- "*" Cotizacion : emite
    Insumo "1" *-- "*" MovimientoInventario : audita
    Pedido "0..1" <-- "*" MovimientoInventario : origina
    RutaDespacho "1" *-- "*" Despacho : agrupa
    Pedido "1" <-- "*" Despacho : entrega
    Usuario "1" <-- "*" RutaDespacho : conduce
```

---

## 2. Vista de Procesos (Concurrencia y Transacciones)

### Confirmación Atómica de Pedido y Descuento de Stock (BOM)

```mermaid
sequenceDiagram
    autonumber
    actor Vendedor as Vendedor / Admin
    participant View as PedidoViewSet / Servicio
    participant DB as PostgreSQL
    participant Stock as StockService

    Vendedor->>View: POST /api/pedidos/{id}/confirmar/ (version=N)
    View->>DB: BEGIN transaction.atomic()
    View->>DB: SELECT * FROM Pedido WHERE id={id} FOR UPDATE
    alt Versión desactualizada
        View-->>Vendedor: 409 Conflict ("El pedido fue modificado por otro usuario")
    end
    View->>Stock: descontar_stock_pedido(pedido, usuario)
    Stock->>DB: SELECT * FROM Insumo WHERE id IN (...) ORDER BY id FOR UPDATE
    Note over Stock,DB: Bloqueo ordenado por ID evita deadlocks
    alt Stock insuficiente o insumo vencido
        Stock-->>View: ValidationError (Rollback completo)
        View-->>Vendedor: 400 Bad Request (Lista de faltantes)
    else Stock suficiente
        Stock->>DB: UPDATE Insumo SET stock_actual = stock_actual - requerido
        Stock->>DB: INSERT INTO MovimientoInventario (SALIDA)
        Stock->>DB: UPDATE Pedido SET inventario_descontado = True
        View->>DB: UPDATE Cotizacion SET estado = 'ACEPTADA'
        View->>DB: UPDATE Pedido SET estado = 'CONFIRMADO', version = N + 1
        View->>DB: INSERT INTO HistorialEstadoPedido ('COTIZADO' → 'CONFIRMADO')
        View->>DB: COMMIT
        View-->>Vendedor: 200 OK (Pedido confirmado en Kanban)
    end
```

---

## 3. Vista de Desarrollo (Estructura de Apps y Capas)

```mermaid
graph TD
    subgraph Capa_Presentacion ["Capa de Presentación"]
        WebViews[Vistas Django Templates HTML+JS]
        APIViews[ViewSets Django REST Framework]
        AdminPanel[Django Admin Personalizado]
    end

    subgraph Capa_Servicios ["Capa de Servicios de Dominio"]
        CotizacionService[cotizacion_service.py]
        StockService[stock_service.py BOM]
        DespachoService[despacho_service.py]
    end

    subgraph Capa_Datos ["Capa de Persistencia y Modelos"]
        ModUsuarios[apps.usuarios: Usuario]
        ModCatalogo[apps.catalogo: Insumo, Receta, BOM]
        ModPedidos[apps.pedidos: Pedido, Detalle, Cotizacion]
        ModInventario[apps.inventario: MovimientoInventario]
        ModDespachos[apps.despachos: RutaDespacho, Despacho]
    end

    WebViews --> CotizacionService
    WebViews --> DespachoService
    APIViews --> CotizacionService
    APIViews --> StockService
    APIViews --> DespachoService
    AdminPanel --> CotizacionService

    CotizacionService --> ModPedidos
    CotizacionService --> StockService
    StockService --> ModCatalogo
    StockService --> ModInventario
    DespachoService --> ModDespachos
    DespachoService --> ModPedidos
```

---

## 4. Vista Física (Despliegue en AWS EC2 Monolito)

```mermaid
graph LR
    ClientBrowser["Navegador Cliente / Celular / Tablet"]
    
    subgraph AWS_EC2 ["Instancia AWS EC2 (Ubuntu 24.04 LTS)"]
        Nginx["Nginx (Puerto 80 HTTP)"]
        StaticMedia["Disco Local (/staticfiles & /media)"]
        Gunicorn["Gunicorn WSGI (127.0.0.1:8000)"]
        DjangoApp["Aplicación Django 5.x"]
        PostgreSQL["PostgreSQL 16 (127.0.0.1:5432)"]
    end

    ClientBrowser -->|HTTP:80| Nginx
    Nginx -->|Sirve /static/ y /media/| StaticMedia
    Nginx -->|Proxy Pass /| Gunicorn
    Gunicorn --> DjangoApp
    DjangoApp -->|Unix Socket / TCP local| PostgreSQL
```

---

## 5. Escenarios (Casos de Uso Principales)

1. **Cotización y Venta:** El vendedor crea un pedido en `BORRADOR` con ingredientes y personalización. Emite la cotización formal pasando el estado a `COTIZADO`.
2. **Confirmación y Descuento de Bodega:** El cliente aprueba y abona. Se confirma el pedido descontando automáticamente las materias primas según el BOM en una transacción atómica.
3. **Producción Kanban en Cocina:** El equipo de cocina visualiza el pedido en la columna *Recibido* y lo avanza por *En Preparación*, *Horneado/Decorado*, *Control de Calidad* hasta *Listo*.
4. **Logística y Despacho:** Se agrupan pedidos listos en una `RutaDespacho`. El repartidor inicia la ruta, accede a las direcciones en Google Maps y confirma la entrega registrando la firma digital o fotografía del cliente.
