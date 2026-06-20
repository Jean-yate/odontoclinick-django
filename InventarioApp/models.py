from django.db import models
from django.conf import settings 

class CategoriaProducto(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria

    class Meta:
        managed = True
        db_table = 'categoria_producto'


class Empresa(models.Model):
    id_empresa = models.AutoField(primary_key=True)
    nombre_empresa = models.CharField(max_length=255, unique=True, verbose_name="Nombre de la Empresa")
    nit = models.CharField(max_length=50, unique=True, verbose_name="NIT")
    es_proveedor = models.BooleanField(default=True, verbose_name="¿Es Proveedor?")
    es_comprador = models.BooleanField(default=False, verbose_name="¿Es Comprador?")

    def __str__(self):
        return self.nombre_empresa

    class Meta:
        managed = True
        db_table = 'empresa'


class Producto(models.Model):
    UNIDADES = [
        ('UN', 'Unidad'),
        ('ML', 'Mililitros'),
        ('GR', 'Gramos'),
        ('CJ', 'Caja'),
    ]

    id_producto = models.AutoField(primary_key=True)
    codigo_producto = models.CharField(unique=True, max_length=50, blank=True, null=True)
    nombre_producto = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    id_categoria = models.ForeignKey(CategoriaProducto, models.PROTECT, db_column='id_categoria')
    precio_venta = models.IntegerField(verbose_name="Precio de Venta Base")
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5)
    
    unidad_medida = models.CharField(max_length=2, choices=UNIDADES, default='UN')
    fecha_vencimiento = models.DateField(blank=True, null=True)
    activo = models.IntegerField(default=1)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_producto} ({self.stock_actual} {self.unidad_medida})"

    class Meta:
        managed = True
        db_table = 'producto'


class ProductoEmpresa(models.Model):
    id_producto_empresa = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column='id_producto', related_name='proveedores_lotes')
    id_empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='id_empresa')
    precio_compra_proveedor = models.IntegerField(verbose_name="Precio de Compra de este Proveedor")
    stock_proveedor = models.IntegerField(default=0, verbose_name="Stock disponible de este proveedor")
    fecha_ultimo_abastecimiento = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'producto_empresa'
        unique_together = ('id_producto', 'id_empresa', 'precio_compra_proveedor')

    def __str__(self):
        return f"{self.id_producto.nombre_producto} - {self.id_empresa.nombre_empresa} (${self.precio_compra_proveedor})"


class MovimientoInventario(models.Model):
    TIPOS = [
        ('ENTRADA', 'Entrada (Compra/Ajuste)'),
        ('SALIDA', 'Salida (Consumo/Pérdida)'),
    ]
    id_movimiento = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey('Producto', on_delete=models.CASCADE, db_column='id_producto')
    id_usuario = models.ForeignKey(
        'CuentasApp.Usuario', 
        on_delete=models.SET_NULL, 
        db_column='id_usuario', 
        null=True, 
        blank=True,
        related_name='movimientos_operados'
    )
    
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_nuevo = models.IntegerField()
    motivo = models.CharField(max_length=255, blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    id_cita = models.ForeignKey(
        'CitaApp.Cita', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_cita',
        related_name='insumos_consumidos'
    )
    empresa_asociada = models.ForeignKey(
        'Empresa', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_empresa'
    )
    cliente_externo = models.ForeignKey(
        'CuentasApp.Usuario', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_cliente_externo',
        related_name='compras_materiales_personales'
    )
    precio_transaccion = models.IntegerField(null=True, blank=True, help_text="Precio cobrado o pagado por unidad")

    class Meta:
        managed = True
        db_table = 'movimiento_inventario'

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.id_producto.nombre_producto} ({self.cantidad})"