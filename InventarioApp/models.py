from django.db import models
from django.conf import settings # Para referenciar al usuario de forma segura

class CategoriaProducto(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria

    class Meta:
        managed = True
        db_table = 'categoria_producto'

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
    id_categoria = models.ForeignKey(CategoriaProducto, models.PROTECT, db_column='id_categoria') # PROTECT evita borrar categorías con productos
    
    # Precios y Stock
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5)
    
    # NUEVO: Unidad de medida para reportes precisos
    unidad_medida = models.CharField(max_length=2, choices=UNIDADES, default='UN')
    
    fecha_vencimiento = models.DateField(blank=True, null=True)
    activo = models.IntegerField(default=1) # 1 activo, 0 inactivo
    fecha_creacion = models.DateTimeField(auto_now_add=True) # Se llena sola

    def __str__(self):
        return f"{self.nombre_producto} ({self.stock_actual} {self.unidad_medida})"

    class Meta:
        managed = True
        db_table = 'producto'

class MovimientoInventario(models.Model):
    TIPOS = [
        ('ENTRADA', 'Entrada (Compra/Ajuste)'),
        ('SALIDA', 'Salida (Consumo/Pérdida)'),
    ]

    id_movimiento = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        'Producto', 
        on_delete=models.CASCADE, 
        db_column='id_producto'
    )
    
    id_usuario = models.ForeignKey(
        'CuentasApp.Usuario', 
        on_delete=models.SET_NULL, 
        db_column='id_usuario',
        null=True, 
        blank=True
    )
    
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_nuevo = models.IntegerField()
    motivo = models.CharField(max_length=255, blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'movimiento_inventario'