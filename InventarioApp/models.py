from django.db import models
from django.conf import settings
from EmpresaApp.models import Empresa


class CategoriaProducto(models.Model):
    id_categoria     = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(unique=True, max_length=100)
    descripcion      = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria

    class Meta:
        managed  = True
        db_table = 'categoria_producto'


class Producto(models.Model):
    UNIDADES = [
        ('UN', 'Unidad'),
        ('ML', 'Mililitros'),
        ('GR', 'Gramos'),
        ('CJ', 'Caja'),
    ]

    id_producto      = models.AutoField(primary_key=True)
    codigo_producto  = models.CharField(unique=True, max_length=50, blank=True, null=True)
    nombre_producto  = models.CharField(max_length=255)
    descripcion      = models.TextField(blank=True, null=True)
    id_categoria     = models.ForeignKey(
        CategoriaProducto, models.PROTECT, db_column='id_categoria'
    )
    precio_venta     = models.IntegerField(verbose_name="Precio de Venta Base")
    stock_actual     = models.IntegerField(default=0)
    stock_minimo     = models.IntegerField(default=5)
    unidad_medida    = models.CharField(max_length=2, choices=UNIDADES, default='UN')
    fecha_vencimiento = models.DateField(blank=True, null=True)
    activo           = models.IntegerField(default=1)
    fecha_creacion   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_producto} ({self.stock_actual} {self.unidad_medida})"

    class Meta:
        managed  = True
        db_table = 'producto'


class ProductoEmpresa(models.Model):
    """
    Relación producto-proveedor con precio de compra.
    Cada combinación (producto, empresa, precio) es un proveedor-precio distinto.
    """
    id_producto_empresa         = models.AutoField(primary_key=True)
    id_producto                 = models.ForeignKey(
        Producto, on_delete=models.CASCADE,
        db_column='id_producto', related_name='proveedores_lotes'
    )
    id_empresa                  = models.ForeignKey(
        'EmpresaApp.Empresa', on_delete=models.CASCADE, db_column='id_empresa'
    )
    precio_compra_proveedor     = models.IntegerField(
        verbose_name="Precio de Compra de este Proveedor"
    )
    stock_proveedor             = models.IntegerField(
        default=0, verbose_name="Stock disponible de este proveedor"
    )
    fecha_ultimo_abastecimiento = models.DateTimeField(auto_now=True)

    class Meta:
        managed      = True
        db_table     = 'producto_empresa'
        unique_together = ('id_producto', 'id_empresa', 'precio_compra_proveedor')

    def __str__(self):
        return (
            f"{self.id_producto.nombre_producto} - "
            f"{self.id_empresa.nombre_empresa} (${self.precio_compra_proveedor})"
        )


# ─── NUEVO: Lote de compra ────────────────────────────────────────────────────
class LoteCompra(models.Model):
    """
    Cada vez que entra mercancía de un proveedor se crea un lote.
    Permite saber exactamente cuántas unidades quedan de cada compra
    y a qué precio se compraron → base para FIFO y cálculo real de ganancia.

    Las SALIDAs referencian lotes a través de DetalleSalida.
    """
    id_lote          = models.AutoField(primary_key=True)
    id_producto      = models.ForeignKey(
        Producto, on_delete=models.CASCADE,
        db_column='id_producto', related_name='lotes'
    )
    id_empresa       = models.ForeignKey(
        'EmpresaApp.Empresa', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_empresa',
        related_name='lotes_proveidos'
    )
    precio_compra    = models.IntegerField(
        verbose_name="Precio pagado por unidad en esta compra"
    )
    cantidad_inicial = models.IntegerField(verbose_name="Unidades compradas en este lote")
    cantidad_disponible = models.IntegerField(
        verbose_name="Unidades aún no vendidas de este lote"
    )
    fecha_compra     = models.DateTimeField(auto_now_add=True)
    id_movimiento_entrada = models.OneToOneField(
        'MovimientoInventario', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lote_generado',
        help_text="El MovimientoInventario ENTRADA que creó este lote"
    )

    class Meta:
        managed  = True
        db_table = 'lote_compra'
        ordering = ['fecha_compra']   # FIFO: el más viejo primero

    def __str__(self):
        return (
            f"Lote #{self.id_lote} · {self.id_producto.nombre_producto} · "
            f"{self.cantidad_disponible}/{self.cantidad_inicial} uds. "
            f"@ ${self.precio_compra}"
        )


# ─── NUEVO: Detalle de salida por lote ───────────────────────────────────────
class DetalleSalida(models.Model):
    """
    Cuando se hace una SALIDA, puede consumir unidades de varios lotes (FIFO).
    Esta tabla registra cuántas unidades de cada lote se usaron en esa salida.

    Ejemplo: vendo 30 unidades.
      - 20 venían del lote A (compradas a $1500) → DetalleSalida(lote=A, cantidad=20)
      - 10 venían del lote B (compradas a $2000) → DetalleSalida(lote=B, cantidad=10)
    Así podemos calcular el costo real de la venta:
      costo = 20×$1500 + 10×$2000 = $50.000
    """
    id_detalle       = models.AutoField(primary_key=True)
    id_movimiento    = models.ForeignKey(
        'MovimientoInventario', on_delete=models.CASCADE,
        db_column='id_movimiento', related_name='detalles_lote'
    )
    id_lote          = models.ForeignKey(
        LoteCompra, on_delete=models.PROTECT,
        db_column='id_lote', related_name='salidas'
    )
    cantidad         = models.IntegerField(
        verbose_name="Unidades tomadas de este lote"
    )
    precio_compra    = models.IntegerField(
        verbose_name="Precio de compra al momento de la salida (snapshot)"
    )

    class Meta:
        managed  = True
        db_table = 'detalle_salida'

    def __str__(self):
        return (
            f"Salida #{self.id_movimiento_id} · "
            f"Lote #{self.id_lote_id} · {self.cantidad} uds."
        )


class MovimientoInventario(models.Model):
    TIPOS = [
        ('ENTRADA', 'Entrada (Compra/Ajuste)'),
        ('SALIDA',  'Salida (Consumo/Pérdida)'),
    ]
    id_movimiento   = models.AutoField(primary_key=True)
    id_producto     = models.ForeignKey(
        'Producto', on_delete=models.CASCADE, db_column='id_producto'
    )
    id_usuario      = models.ForeignKey(
        'CuentasApp.Usuario',
        on_delete=models.SET_NULL,
        db_column='id_usuario',
        null=True, blank=True,
        related_name='movimientos_operados'
    )
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS)
    cantidad        = models.IntegerField()
    stock_anterior  = models.IntegerField()
    stock_nuevo     = models.IntegerField()
    motivo          = models.CharField(max_length=255, blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    id_cita         = models.ForeignKey(
        'CitaApp.Cita',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='id_cita',
        related_name='insumos_consumidos'
    )
    empresa_asociada = models.ForeignKey(
        'EmpresaApp.Empresa',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='id_empresa'
    )
    cliente_externo = models.ForeignKey(
        'CuentasApp.Usuario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='id_cliente_externo',
        related_name='compras_materiales_personales'
    )
    precio_transaccion = models.IntegerField(
        null=True, blank=True,
        help_text="Precio cobrado (SALIDA/venta) o pagado (ENTRADA/compra) por unidad"
    )
    # ── NUEVO: costo promedio ponderado al momento de la salida ───────────────
    # Se calcula automáticamente en salida_stock() usando los lotes FIFO.
    # Permite mostrar la ganancia real sin tener que recorrer DetalleSalida.
    costo_unitario_salida = models.IntegerField(
        null=True, blank=True,
        help_text="Costo promedio ponderado por unidad según lotes FIFO consumidos"
    )

    class Meta:
        managed  = True
        db_table = 'movimiento_inventario'

    def __str__(self):
        return (
            f"{self.tipo_movimiento} - "
            f"{self.id_producto.nombre_producto} ({self.cantidad})"
        )